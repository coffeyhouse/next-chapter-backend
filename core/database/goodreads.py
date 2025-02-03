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

logger = logging.getLogger(__name__)


def merge_book_data(existing: dict, new_data: dict) -> dict:
    """
    Merge new book data with the existing record.
    Only update fields that differ.
    Handles source and the date fields separately.
    
    Args:
        existing: dict from the database.
        new_data: dict scraped or imported from another source.
        
    Returns:
        A merged dict with updated fields.
    """
    # List of fields that we compare and update if they differ.
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
    
    # Preserve existing source if it is "library"; otherwise, use new data (defaulting to "scrape")
    if existing.get('source') == 'library':
        merged['source'] = existing['source']
    else:
        merged['source'] = new_data.get('source', 'scrape')
    
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
        This function resolves the book data, then imports the base book data,
        along with any Calibre-specific data and relationships.
        """
        try:
            goodreads_id = calibre_data['goodreads_id']
            resolver = BookResolver(scrape=True)
            
            # Get the fully resolved book data (which may trigger a full scrape)
            final_book_data = resolver.resolve_book(goodreads_id)
            if not final_book_data:
                print(f"Failed to resolve a proper edition for book ID: {goodreads_id}")
                return False
            
            with self._get_connection() as conn:
                conn.execute("BEGIN")
                try:
                    # Import the base book data (using our diff-and-merge logic)
                    if not self._import_base_book_data(conn, final_book_data):
                        raise Exception("Failed to import base book data")
                    
                    # Import Calibre-specific data if provided
                    if calibre_data and 'calibre_id' in calibre_data:
                        if not self._import_calibre_data(conn, calibre_data, final_book_data['work_id']):
                            raise Exception("Failed to import Calibre data")
                    
                    # Import relationships (authors, series, genres)
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
                # Merge the new data with the existing data.
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
                    'source': new_book_data.get('source', 'scrape'),
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
            
            # Update the book's source to "library" and record the Calibre id.
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
            Tuple of (processed_count, imported_count).
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
                        book_data = {
                            'goodreads_id': book['goodreads_id'],
                            'title': book['title']
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
