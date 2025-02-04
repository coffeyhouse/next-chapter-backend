# core/database/goodreads.py

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import sqlite3
import logging

from .base import BaseDB
from .queries import BookQueries, AuthorQueries, SeriesQueries, StatsQueries
from .schema import init_db
from ..scrapers.book_scraper import BookScraper
from core.resolvers.book_resolver import BookResolver
from ..scrapers.series_scraper import SeriesScraper
from ..scrapers.author_scraper import AuthorScraper
from ..scrapers.author_books_scraper import AuthorBooksScraper
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Helper functions for merging book data and determining source priority.
# -----------------------------------------------------------------------------

def choose_source(existing_source: str, new_source: Optional[str]) -> str:
    """
    Determine which source to keep based on a priority mapping.
    
    For example:
      - 'library' is highest priority.
      - 'series', 'author', and 'similar' get priority 2.
      - 'scrape' is the default (priority 1).
    
    If the new source is provided and its priority is greater than or equal
    to the existing source, then use the new source. Otherwise, keep the existing one.
    """
    priority = {
        'library': 3,
        'series': 2,
        'author': 2,
        'similar': 2,
        'scrape': 1
    }
    
    if not new_source:
        return existing_source or 'scrape'
    if not existing_source:
        return new_source
    if priority.get(new_source, 0) >= priority.get(existing_source, 0):
        return new_source
    return existing_source

def merge_book_data(existing: dict, new_data: dict) -> dict:
    """
    Merge new book data with the existing record.
    Only update fields that differ.
    Handles source and the date fields separately.
    
    Args:
        existing: Dictionary of the existing database record.
        new_data: Dictionary of the new data (scraped or imported).
        
    Returns:
        A merged dictionary with updated fields.
    """
    # Fields that we want to update if they differ.
    updatable_fields = [
        'title', 'work_id', 'published_date', 'published_state',
        'language', 'pages', 'isbn', 'goodreads_rating',
        'goodreads_votes', 'description', 'image_url', 'hidden'
    ]
    
    merged = {}
    # Always include the primary key.
    merged['goodreads_id'] = existing['goodreads_id']
    
    # For each updatable field, update only if the new value differs.
    for field in updatable_fields:
        if field in new_data and new_data[field] != existing.get(field):
            merged[field] = new_data[field]
        else:
            merged[field] = existing.get(field)
    
    # For source, use choose_source to decide whether to update.
    existing_source = existing.get('source', 'scrape')
    new_source = new_data.get('source')  # Could be 'series', 'author', 'similar', etc.
    print("existing_source", existing_source, "new_source", new_source)
    merged['source'] = choose_source(existing_source, new_source)
    
    # Always preserve the original created_at timestamp.
    merged['created_at'] = existing.get('created_at')
    
    # Always update last_synced_at to now.
    now = datetime.now().isoformat()
    merged['last_synced_at'] = now

    # Update updated_at only if any updatable field has changed.
    differences = any(new_data.get(field) != existing.get(field) for field in updatable_fields)
    if differences:
        merged['updated_at'] = now
    else:
        merged['updated_at'] = existing.get('updated_at')
    
    return merged

# -----------------------------------------------------------------------------
# Main class for the Goodreads database operations.
# -----------------------------------------------------------------------------

class GoodreadsDB(BaseDB):
    def __init__(self, db_path: str = "books.db"):
        super().__init__(db_path)
        self._ensure_db_exists()
        self.book_scraper = BookScraper(scrape=True)
    
    def _ensure_db_exists(self):
        if not Path(self.db_path).exists():
            init_db(self.db_path)
    
    def _import_single_book(self, calibre_data: Dict[str, Any]) -> bool:
        """
        Import a single book from any source with full resolution.
        Resolves the book data, then imports the base book data, along with
        any Calibre-specific data and relationships.
        
        NOTE: To allow a series (or author/similar) sync to override the default
        'scrape' source, we update the resolved data with any keys (e.g. 'source')
        that are passed in via calibre_data.
        """
        try:
            goodreads_id = calibre_data['goodreads_id']
            resolver = BookResolver(scrape=True)
            
            # Resolve the full book data (this will have 'source': 'scrape')
            final_book_data = resolver.resolve_book(goodreads_id)
            if not final_book_data:
                print(f"Failed to resolve a proper edition for book ID: {goodreads_id}")
                return False

            # Update final_book_data with any provided override (e.g. source)
            if 'source' in calibre_data:
                final_book_data['source'] = calibre_data['source']         
            
            with self._get_connection() as conn:
                conn.execute("BEGIN")
                try:
                    # Import the base book data using our diff-and-merge logic.
                    if not self._import_base_book_data(conn, final_book_data):
                        raise Exception("Failed to import base book data")
                    
                    # If Calibre data is provided, import Calibre-specific information.
                    if calibre_data and 'calibre_id' in calibre_data:
                        if not self._import_calibre_data(conn, calibre_data, final_book_data['work_id']):
                            raise Exception("Failed to import Calibre data")
                    
                    # Import relationships (authors, series, genres).
                    if not self._import_authors(conn, final_book_data['work_id'], final_book_data.get('authors', [])):
                        raise Exception("Failed to import authors")
                    if not self._import_series(conn, final_book_data['work_id'], final_book_data.get('series', [])):
                        raise Exception("Failed to import series")
                    if not self._import_genres(conn, final_book_data['work_id'], final_book_data.get('genres', [])):
                        raise Exception("Failed to import genres")
                        
                    conn.execute("COMMIT")
                    return True
                    
                except Exception as e:
                    conn.execute("ROLLBACK")
                    print(f"Transaction failed: {e}")
                    return False
                    
        except Exception as e:
            print(f"Error importing book: {e}")
            return False
        
    def _import_base_book_data(self, conn: sqlite3.Connection, new_book_data: Dict[str, Any]) -> bool:
        """
        Import core book data without Calibre-specific information.
        If a record already exists, merge the new data with the existing record,
        updating only fields that are different (and preserving source and date fields).
        """
        try:
            # Check if the book already exists.
            cursor = conn.execute(
                "SELECT * FROM book WHERE goodreads_id = ?",
                (new_book_data['goodreads_id'],)
            )
            row = cursor.fetchone()
            if row:
                # Convert the existing row to a dictionary.
                existing = dict(zip([col[0] for col in cursor.description], row))
                # Merge the new data with the existing record.
                merged_data = merge_book_data(existing, new_book_data)
                # Prepare an UPDATE that sets only the merged fields.
                update_fields = [field for field in merged_data if field != 'goodreads_id']
                set_clause = ', '.join(f"{field}=?" for field in update_fields)
                sql = f"UPDATE book SET {set_clause} WHERE goodreads_id = ?"
                values = [merged_data[field] for field in update_fields] + [merged_data['goodreads_id']]
                conn.execute(sql, values)
            else:
                # If this is a new record, set all date fields to now.
                now = datetime.now().isoformat()
                book = {
                    'goodreads_id': new_book_data['goodreads_id'],
                    'title': new_book_data.get('title'),
                    'work_id': new_book_data.get('work_id'),
                    'published_date': new_book_data.get('published_date'),
                    'published_state': new_book_data.get('published_state'),
                    'language': new_book_data.get('language'),
                    'pages': new_book_data.get('pages'),
                    'isbn': new_book_data.get('isbn'),
                    'goodreads_rating': new_book_data.get('goodreads_rating'),
                    'goodreads_votes': new_book_data.get('goodreads_votes'),
                    'description': new_book_data.get('description'),
                    'image_url': new_book_data.get('image_url'),
                    'source': new_book_data.get('source'),
                    'hidden': new_book_data.get('hidden', False),
                    'created_at': now,
                    'updated_at': now,
                    'last_synced_at': now,
                }
                fields = list(book.keys())
                placeholders = ','.join(['?'] * len(fields))
                sql = f"INSERT INTO book ({','.join(fields)}) VALUES ({placeholders})"
                conn.execute(sql, [book[field] for field in fields])
            return True
        except Exception as e:
            print(f"Error importing base book data: {e}")
            return False

    def _import_calibre_data(self, conn: sqlite3.Connection, calibre_data: Dict[str, Any], work_id: str) -> bool:
        """Import Calibre-specific data into the library table."""
        try:
            now = datetime.now().isoformat()
            
            # Update the book's source to 'library' and record the Calibre ID.
            conn.execute("""
                UPDATE book 
                SET source = 'library', calibre_id = ?
                WHERE work_id = ?
            """, (calibre_data['calibre_id'], work_id))
            
            # Insert the library-specific record.
            library = {
                'title': calibre_data['title'],
                'calibre_id': calibre_data['calibre_id'],
                'goodreads_id': calibre_data['goodreads_id'],
                'work_id': work_id,
                'isbn': calibre_data['isbn'],
                'last_synced_at': now,
                'created_at': now,
                'updated_at': now,
            }
            
            fields = list(library.keys())
            placeholders = ','.join(['?'] * len(fields))
            
            conn.execute(f"""
                INSERT INTO library ({','.join(fields)})
                VALUES ({placeholders})
                ON CONFLICT(goodreads_id) DO UPDATE SET
                {','.join(f"{field}=excluded.{field}" for field in fields if field != 'goodreads_id')}
            """, [library[field] for field in fields])
            
            return True
            
        except Exception as e:
            print(f"Error importing Calibre data: {e}")
            return False

    def import_calibre_books(self, calibre_path: str, limit: Optional[int] = None) -> Tuple[int, int]:
        """Import books from Calibre that aren't already in the library table."""
        try:
            # Get existing Goodreads IDs from the library table.
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT goodreads_id FROM library")
                existing_ids = {row[0] for row in cursor.fetchall()}
            
            # Get books from the Calibre database.
            with sqlite3.connect(calibre_path) as calibre_conn:
                query = """
                    SELECT 
                        books.id AS calibre_id,
                        books.title,
                        gr.val AS goodreads_id,
                        isbn.val AS isbn,
                        warren_read.value AS warren_last_read,
                        ruth_read.value AS ruth_last_read
                    FROM books
                    LEFT JOIN identifiers gr 
                        ON gr.book = books.id 
                        AND gr.type = 'goodreads'
                    LEFT JOIN identifiers isbn
                        ON isbn.book = books.id 
                        AND isbn.type = 'isbn'
                    LEFT JOIN custom_column_6 warren_read
                        ON warren_read.book = books.id
                    LEFT JOIN custom_column_14 ruth_read
                        ON ruth_read.book = books.id
                    WHERE gr.val IS NOT NULL
                """
                
                cursor = calibre_conn.execute(query)
                books = cursor.fetchall()
                
                # Filter out books that already exist and apply a limit if provided.
                new_books = [book for book in books if book[2] not in existing_ids]
                if limit:
                    new_books = new_books[:limit]
                
                print(f"Found {len(new_books)} new books to import")
                
                processed = 0
                imported = 0
                
                for book in new_books:
                    calibre_data = dict(zip(
                        ['calibre_id', 'title', 'goodreads_id', 'isbn', 
                         'warren_last_read', 'ruth_last_read'], 
                        book
                    ))
                    
                    if self._import_single_book(calibre_data):
                        imported += 1
                        print(f"Successfully imported {calibre_data['title']} ({imported}/{len(new_books)})")
                    else:
                        print(f"Failed to import {calibre_data['title']}")
                    processed += 1
                
                return processed, imported
                
        except Exception as e:
            print(f"Error importing from Calibre: {e}")
            return 0, 0   

    def _import_authors(self, conn: sqlite3.Connection, work_id: str, authors: List[Dict[str, Any]]) -> bool:
        """Import authors and book-author relationships."""
        try:
            now = datetime.now().isoformat()
            
            for author in authors:
                # Insert author record.
                author_data = {
                    'goodreads_id': author['goodreads_id'],
                    'name': author['name'],
                    'created_at': now,
                    'updated_at': now
                }
                
                fields = list(author_data.keys())
                placeholders = ','.join(['?'] * len(fields))
                conn.execute(f"""
                    INSERT INTO author ({','.join(fields)})
                    VALUES ({placeholders})
                    ON CONFLICT(goodreads_id) DO UPDATE SET
                    {','.join(f"{field}=excluded.{field}" for field in fields if field != 'goodreads_id')}
                """, [author_data[field] for field in fields])
                
                # Insert book-author relationship.
                relation_data = {
                    'work_id': work_id,
                    'author_id': author['goodreads_id'],
                    'role': author['role'],
                    'created_at': now,
                    'updated_at': now
                }
                
                fields = list(relation_data.keys())
                placeholders = ','.join(['?'] * len(fields))
                conn.execute(f"""
                    INSERT INTO book_author ({','.join(fields)})
                    VALUES ({placeholders})
                    ON CONFLICT(work_id, author_id) DO UPDATE SET
                    {','.join(f"{field}=excluded.{field}" for field in fields if field not in ['work_id', 'author_id'])}
                """, [relation_data[field] for field in fields])
            
            return True
            
        except Exception as e:
            print(f"Error importing authors: {e}")
            return False

    def _import_series(self, conn: sqlite3.Connection, work_id: str, series_list: List[Dict[str, Any]]) -> bool:
        """Import series and book-series relationships."""
        try:
            now = datetime.now().isoformat()
            
            for series in series_list:
                if not series['goodreads_id']:
                    continue
                    
                # Insert series record.
                series_data = {
                    'goodreads_id': series['goodreads_id'],
                    'title': series['name'],
                    'created_at': now,
                    'updated_at': now
                }
                
                fields = list(series_data.keys())
                placeholders = ','.join(['?'] * len(fields))
                conn.execute(f"""
                    INSERT INTO series ({','.join(fields)})
                    VALUES ({placeholders})
                    ON CONFLICT(goodreads_id) DO UPDATE SET
                    {','.join(f"{field}=excluded.{field}" for field in fields if field != 'goodreads_id')}
                """, [series_data[field] for field in fields])
                
                # Insert book-series relationship.
                relation_data = {
                    'work_id': work_id,
                    'series_id': series['goodreads_id'],
                    'series_order': series['order'],
                    'created_at': now,
                    'updated_at': now
                }
                
                fields = list(relation_data.keys())
                placeholders = ','.join(['?'] * len(fields))
                conn.execute(f"""
                    INSERT INTO book_series ({','.join(fields)})
                    VALUES ({placeholders})
                    ON CONFLICT(work_id, series_id) DO UPDATE SET
                    {','.join(f"{field}=excluded.{field}" for field in fields if field not in ['work_id', 'series_id'])}
                """, [relation_data[field] for field in fields])
            
            return True
            
        except Exception as e:
            print(f"Error importing series: {e}")
            return False

    def _import_genres(self, conn: sqlite3.Connection, work_id: str, genres: List[Dict[str, Any]]) -> bool:
        """Import genres and book-genre relationships."""
        try:
            now = datetime.now().isoformat()
            
            for genre in genres:
                # Ensure the genre exists and get its ID.
                cursor = conn.execute(
                    "SELECT id FROM genre WHERE name = ?",
                    (genre['name'],)
                )
                result = cursor.fetchone()
                
                if result:
                    genre_id = result[0]
                else:
                    cursor = conn.execute(
                        """
                        INSERT INTO genre (name, created_at, updated_at)
                        VALUES (?, ?, ?)
                        """,
                        (genre['name'], now, now)
                    )
                    genre_id = cursor.lastrowid
                
                # Insert book-genre relationship.
                relation_data = {
                    'work_id': work_id,
                    'genre_id': genre_id,
                    'created_at': now,
                    'updated_at': now
                }
                
                fields = list(relation_data.keys())
                placeholders = ','.join(['?'] * len(fields))
                conn.execute(f"""
                    INSERT INTO book_genre ({','.join(fields)})
                    VALUES ({placeholders})
                    ON CONFLICT(work_id, genre_id) DO UPDATE SET
                    {','.join(f"{field}=excluded.{field}" for field in fields if field not in ['work_id', 'genre_id'])}
                """, [relation_data[field] for field in fields])
            
            return True
            
        except Exception as e:
            print(f"Error importing genres: {e}")
            return False

    def sync_series(self, days_old: int = 30, limit: int = None) -> Tuple[int, int]:
        """
        Sync unsynced series by scraping their pages and importing their books.
        
        Args:
            days_old: Sync series not updated in this many days.
            limit: Maximum number of series to sync.
            
        Returns:
            A tuple of (processed_count, imported_count).
        """
        try:
            # Get unsynced series.
            series_queries = SeriesQueries(self)
            unsynced_series = series_queries.get_unsynced_series(days_old)
            
            if not unsynced_series:
                logger.info("No unsynced series found")
                return 0, 0
            
            # Apply a limit if specified.
            if limit:
                unsynced_series = unsynced_series[:limit]
            
            # Initialize the series scraper.
            series_scraper = SeriesScraper(scrape=True)
            processed = 0
            imported = 0
            
            for series in unsynced_series:
                series_id = series['goodreads_id']
                logger.info(f"Syncing series: {series['title']} ({series_id})")
                
                # Scrape series data.
                series_data = series_scraper.scrape_series(series_id)
                if not series_data:
                    logger.error(f"Failed to scrape series: {series_id}")
                    continue
                
                # Import each book in the series.
                for book in series_data['books']:
                    if book['goodreads_id']:
                        # Create minimal book data for import.
                        # Here we pass the source as 'series' so that merge_book_data
                        # can update the source if appropriate.
                        book_data = {
                            'goodreads_id': book['goodreads_id'],
                            'title': book['title'],
                            'source': 'series'
                        }
                        
                        if self._import_single_book(book_data):
                            imported += 1
                            logger.info(f"Imported book: {book['title']}")
                        else:
                            logger.error(f"Failed to import book: {book['title']}")
                
                # Update series last_synced_at.
                with self._get_connection() as conn:
                    conn.execute("""
                        UPDATE series 
                        SET last_synced_at = datetime('now')
                        WHERE goodreads_id = ?
                    """, (series_id,))
                
                processed += 1
            
            return processed, imported
            
        except Exception as e:
            logger.error(f"Error syncing series: {e}")
            return 0, 0
        
    def sync_authors(self, days_old: int = 30, limit: int = None) -> Tuple[int, int]:
        """
        Sync unsynced authors by scraping their pages and importing their books.
        
        Args:
            days_old: Sync authors not updated in this many days
            limit: Maximum number of authors to sync
            
        Returns:
            Tuple of (processed_count, imported_count)
        """
        try:
            # Get unsynced authors using our queries class
            author_queries = AuthorQueries(self)
            unsynced_authors = author_queries.get_unsynced_authors(days_old)
            
            if not unsynced_authors:
                logger.info("No unsynced authors found")
                return 0, 0
            
            # Apply limit if specified
            if limit:
                unsynced_authors = unsynced_authors[:limit]
            
            # Initialize our scrapers
            author_scraper = AuthorScraper(scrape=True)
            author_books_scraper = AuthorBooksScraper(scrape=True)
            
            processed = 0
            imported = 0
            
            for author in unsynced_authors:
                author_id = author['goodreads_id']
                logger.info(f"Syncing author: {author['name']} ({author_id})")
                
                # First get the author's updated details
                author_data = author_scraper.scrape_author(author_id)
                if not author_data:
                    logger.error(f"Failed to scrape author: {author_id}")
                    continue
                
                # Update the author record
                now = datetime.now().isoformat()
                author_data['last_synced_at'] = now
                author_data['updated_at'] = now
                
                success, _ = self.upsert('author', author_data, 'goodreads_id')
                if not success:
                    logger.error(f"Failed to update author: {author_id}")
                    continue
                
                # Now get all the author's books
                books_data = author_books_scraper.scrape_author_books(author_id)
                if not books_data:
                    logger.error(f"Failed to scrape books for author: {author_id}")
                    continue
                
                # Import each book
                for book in books_data['books']:
                    if not book['goodreads_id']:
                        continue
                        
                    # Create minimal book data for import
                    # Set source as 'author' so merge_book_data can update appropriately
                    book_data = {
                        'goodreads_id': book['goodreads_id'],
                        'title': book['title'],
                        'source': 'author'
                    }
                    
                    # Add published date if available
                    if book.get('published_date'):
                        book_data['published_date'] = book['published_date']
                    
                    if self._import_single_book(book_data):
                        imported += 1
                        logger.info(f"Imported book: {book['title']}")
                    else:
                        logger.error(f"Failed to import book: {book['title']}")
                
                processed += 1
            
            return processed, imported
            
        except Exception as e:
            logger.error(f"Error syncing authors: {e}")
            return 0, 0

    def delete_book(self, goodreads_id: str) -> bool:
        """Delete a book and its relationships from the database"""
        try:
            with self._get_connection() as conn:
                conn.execute("BEGIN")
                try:
                    # Get the work_id first
                    cursor = conn.execute(
                        "SELECT work_id FROM book WHERE goodreads_id = ?",
                        (goodreads_id,)
                    )
                    result = cursor.fetchone()
                    if not result:
                        return False
                        
                    work_id = result[0]
                    
                    # Delete related records first
                    conn.execute("DELETE FROM book_author WHERE work_id = ?", (work_id,))
                    conn.execute("DELETE FROM book_genre WHERE work_id = ?", (work_id,))
                    conn.execute("DELETE FROM book_series WHERE work_id = ?", (work_id,))
                    conn.execute("DELETE FROM book_similar WHERE work_id = ? OR similar_work_id = ?", (work_id, work_id))
                    conn.execute("DELETE FROM library WHERE work_id = ?", (work_id,))
                    
                    # Finally delete the book
                    conn.execute("DELETE FROM book WHERE goodreads_id = ?", (goodreads_id,))
                    
                    conn.execute("COMMIT")
                    return True
                    
                except Exception as e:
                    conn.execute("ROLLBACK")
                    print(f"Error in transaction: {e}")
                    return False
                    
        except Exception as e:
            print(f"Error deleting book: {e}")
            return False
