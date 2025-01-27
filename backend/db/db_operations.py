import sqlite3
from typing import Dict, List, Any
from pathlib import Path
import logging
from datetime import datetime
from dateutil import parser as date_parser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseOperations:
    def __init__(self, db_path: str = "books.db"):
        self.db_path = db_path
        
    def _get_genre_id(self, conn, genre_name: str) -> int:
        """Get genre ID by name, creating new if needed"""
        # First try to find existing genre
        cursor = conn.execute(
            "SELECT id FROM genres WHERE name = ?", 
            (genre_name,)
        )
        result = cursor.fetchone()
        if result:
            return result[0]
            
        # If not found, get next available ID
        cursor = conn.execute("SELECT MAX(id) FROM genres")
        result = cursor.fetchone()
        next_id = 1 if result[0] is None else result[0] + 1
        
        # Create new genre
        now = datetime.now().isoformat()
        conn.execute(
            """INSERT INTO genres (id, name, created_at, updated_at)
               VALUES (?, ?, ?, ?)""",
            (next_id, genre_name, now, now)
        )
        
        return next_id
        
    def insert_transformed_data(self, tables: Dict[str, List[Dict[str, Any]]]) -> bool:
        """Insert transformed data into the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")

                # Debug: Print available tables and their record counts
                logger.info("Available tables:")
                for table_name, records in tables.items():
                    logger.info(f"{table_name}: {len(records)} records")
                
                # Special handling for genres - process them first
                if 'genre' in tables and tables['genre']:
                    genre_map = {}  # Store old_id -> new_id mapping
                    for genre_record in tables['genre']:
                        # Get or create genre ID
                        genre_name = genre_record['name']
                        new_id = self._get_genre_id(conn, genre_name)
                        genre_map[genre_record['id']] = new_id
                        
                    # Update book_genre records with new IDs
                    if 'book_genre' in tables:
                        for record in tables['book_genre']:
                            record['genre_id'] = genre_map[record['genre_id']]
                
                # Process remaining tables
                insert_order = [
                    ('books', """
                        INSERT OR REPLACE INTO books (
                            goodreads_id, title, published_date, published_state,
                            language, calibre_id, pages, isbn, goodreads_rating,
                            goodreads_votes, description, image_url, similar_books_id,
                            source, hidden, created_at, updated_at, last_synced_at
                        ) VALUES (
                            :goodreads_id, :title, :published_date, :published_state,
                            :language, :calibre_id, :pages, :isbn, :goodreads_rating,
                            :goodreads_votes, :description, :image_url, :similar_books_id,
                            :source, :hidden, :created_at, :updated_at, :last_synced_at
                        )
                    """),
                    ('library', """
                        INSERT OR REPLACE INTO library (
                            title, calibre_id, goodreads_id, isbn,
                            created_at, updated_at, last_synced_at
                        ) VALUES (
                            :title, :calibre_id, :goodreads_id, :isbn,
                            :created_at, :updated_at, :last_synced_at
                        )
                    """),
                    ('users', """
                        INSERT OR REPLACE INTO users (
                            id, name, created_at, updated_at
                        ) VALUES (
                            :id, :name, :created_at, :updated_at
                        )
                    """),
                    ('series', """
                        INSERT OR REPLACE INTO series (
                            goodreads_id, title, created_at, updated_at, last_synced_at
                        ) VALUES (
                            :goodreads_id, :title, :created_at, :updated_at, :last_synced_at
                        )
                    """),
                    ('authors', """
                        INSERT OR REPLACE INTO authors (
                            goodreads_id, name, bio, image_url,
                            created_at, updated_at, last_synced_at
                        ) VALUES (
                            :goodreads_id, :name, :bio, :image_url,
                            :created_at, :updated_at, :last_synced_at
                        )
                    """),
                    ('awards', """
                        INSERT OR REPLACE INTO awards (
                            goodreads_id, name, created_at, updated_at
                        ) VALUES (
                            :goodreads_id, :name, :created_at, :updated_at
                        )
                    """),
                    ('book_series', """
                        INSERT OR REPLACE INTO book_series (
                            book_id, series_id, series_order, created_at, updated_at
                        ) VALUES (
                            :book_id, :series_id, :series_order, :created_at, :updated_at
                        )
                    """),
                    ('author_books', """
                        INSERT OR REPLACE INTO author_books (
                            book_id, author_id, role, created_at, updated_at
                        ) VALUES (
                            :book_id, :author_id, :role, :created_at, :updated_at
                        )
                    """),
                    ('book_genres', """
                        INSERT OR REPLACE INTO book_genres (
                            genre_id, book_id, created_at, updated_at
                        ) VALUES (
                            :genre_id, :book_id, :created_at, :updated_at
                        )
                    """),
                    ('book_awards', """
                        INSERT OR REPLACE INTO book_awards (
                            book_id, award_id, category, year, designation,
                            created_at, updated_at
                        ) VALUES (
                            :book_id, :award_id, :category, :year, :designation,
                            :created_at, :updated_at
                        )
                    """),
                    ('book_users', """
                        INSERT OR REPLACE INTO book_users (
                            book_id, user_id, status, source,
                            started_at, finished_at, created_at, updated_at
                        ) VALUES (
                            :book_id, :user_id, :status, :source,
                            :started_at, :finished_at, :created_at, :updated_at
                        )
                    """),
                    ('similar_books', """
                        INSERT OR REPLACE INTO similar_books (
                            book_id, similar_book_id, created_at, updated_at
                        ) VALUES (
                            :book_id, :similar_book_id, :created_at, :updated_at
                        )
                    """),
                    ('book_editions', """
                        INSERT OR REPLACE INTO book_editions (
                            book_id, edition_id, created_at, updated_at
                        ) VALUES (
                            :book_id, :edition_id, :created_at, :updated_at
                        )
                    """)
                ]
                
                # Process each table in order
                for table_name, insert_sql in insert_order:
                    # Map database table names to transformer table names
                    transformer_mappings = {
                        'books': 'book',
                        'library': 'library',
                        'series': 'series',
                        'book_series': 'book_series',
                        'authors': 'author',
                        'author_books': 'author_book',
                        'genres': 'genre',
                        'book_genres': 'book_genre',
                        'awards': 'award',
                        'book_awards': 'book_award',
                        'users': 'user',
                        'book_users': 'book_user',
                        'similar_books': 'similar_book',
                        'book_editions': 'book_edition'
                    }
                    transformer_table = transformer_mappings.get(table_name)
                    
                    if transformer_table in tables and tables[transformer_table]:
                        try:
                            records = tables[transformer_table]
                            logger.info(f"Processing {table_name} ({transformer_table})")
                            logger.info(f"First record keys: {records[0].keys()}")
                            logger.info(f"First record values: {records[0]}")
                            
                            # Execute insert
                            if records:  # Only try to insert if we have records
                                try:
                                    conn.executemany(insert_sql, records)
                                    logger.info(f"Successfully inserted {len(records)} records into {table_name}")
                                except sqlite3.Error as e:
                                    logger.error(f"SQLite error on {table_name}: {str(e)}")
                                    logger.error(f"SQL: {insert_sql}")
                                    raise
                            
                        except Exception as e:
                            logger.error(f"Error processing {table_name}: {str(e)}")
                            logger.error(f"Transformer table: {transformer_table}")
                            logger.error(f"First record: {records[0] if records else 'No records'}")
                            raise
                
                return True
                
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            return False
            
    def get_stats(self) -> Dict[str, int]:
        """Get record counts for all tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                stats = {}
                
                # Get list of tables
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
                tables = cursor.fetchall()
                
                # Get count for each table
                for (table_name,) in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    stats[table_name] = count
                    
                return stats
                
        except sqlite3.Error as e:
            logger.error(f"Error getting stats: {str(e)}")
            return {}