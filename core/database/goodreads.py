from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import sqlite3
from .base import BaseDB
from .schema import init_db
from ..scrapers.book_scraper import BookScraper
from core.resolvers.book_resolver import BookResolver
import logging

logger = logging.getLogger(__name__)

class GoodreadsDB(BaseDB):
    def __init__(self, db_path: str = "books.db"):
        super().__init__(db_path)
        self._ensure_db_exists()
        self.book_scraper = BookScraper(scrape=True)
    
    def _ensure_db_exists(self):
        if not Path(self.db_path).exists():
            init_db(self.db_path)

    def import_calibre_books(self, calibre_path: str, limit: Optional[int] = None) -> tuple[int, int]:
        """Import books from Calibre that aren't already in the library table"""
        try:
            # Get existing Goodreads IDs from library table
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT goodreads_id FROM library")
                existing_ids = {row[0] for row in cursor.fetchall()}
            
            # Get books from Calibre
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
                
                # Filter out existing books and apply limit
                new_books = [
                    book for book in books 
                    if book[2] not in existing_ids  # index 2 is goodreads_id
                ]
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

    def _import_single_book(self, calibre_data: Dict[str, Any]) -> bool:
        try:
            goodreads_id = calibre_data['goodreads_id']
            resolver = BookResolver(scrape=True)
            
            # Get the fully resolved book data (details from the chosen edition)
            final_book_data = resolver.resolve_book(goodreads_id)
            if not final_book_data:
                print(f"Failed to resolve a proper edition for book ID: {goodreads_id}")
                return False
            
            with self._get_connection() as conn:
                conn.execute("BEGIN")
                try:
                    # Insert the main book record
                    if not self._import_book_data(conn, calibre_data, final_book_data):
                        raise Exception("Failed to import book data")
                    
                    # Now insert related data using the fully scraped edition's details.
                    # Make sure final_book_data has the relationships.
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


    def _import_book_data(self, conn: sqlite3.Connection, calibre_data: Dict[str, Any], 
                         goodreads_data: Dict[str, Any]) -> bool:
        """Import main book data"""
        try:
            now = datetime.now().isoformat()
            
            # Prepare books record
            book = {
                'goodreads_id': goodreads_data['goodreads_id'],
                'title': goodreads_data['title'],
                'work_id': goodreads_data['work_id'],
                'published_date': goodreads_data['published_date'],
                'published_state': goodreads_data['published_state'],
                'language': goodreads_data['language'],
                'calibre_id': calibre_data['calibre_id'],
                'pages': goodreads_data['pages'],
                'isbn': calibre_data['isbn'] or goodreads_data['isbn'],
                'goodreads_rating': goodreads_data['goodreads_rating'],
                'goodreads_votes': goodreads_data['goodreads_votes'],
                'description': goodreads_data['description'],
                'image_url': goodreads_data['image_url'],
                'source': 'library',
                'hidden': False,
                'last_synced_at': now,
                'created_at': now,
                'updated_at': now
            }
            
            # Insert into books table
            fields = list(book.keys())
            placeholders = ','.join(['?'] * len(fields))
            values = [book[field] for field in fields]
            
            conn.execute(f"""
                INSERT INTO book ({','.join(fields)})
                VALUES ({placeholders})
                ON CONFLICT(goodreads_id) DO UPDATE SET
                {','.join(f"{field}=excluded.{field}" for field in fields if field != 'goodreads_id')}
            """, values)
            
            # Insert into library table
            library = {
                'title': calibre_data['title'],
                'calibre_id': calibre_data['calibre_id'],
                'goodreads_id': calibre_data['goodreads_id'],
                'work_id': goodreads_data['work_id'],
                'isbn': calibre_data['isbn'],                
                'last_synced_at': now,
                'created_at': now,
                'updated_at': now,
            }
            
            fields = list(library.keys())
            placeholders = ','.join(['?'] * len(fields))
            values = [library[field] for field in fields]
            
            conn.execute(f"""
                INSERT INTO library ({','.join(fields)})
                VALUES ({placeholders})
                ON CONFLICT(goodreads_id) DO UPDATE SET
                {','.join(f"{field}=excluded.{field}" for field in fields if field != 'goodreads_id')}
            """, values)
            
            return True
            
        except Exception as e:
            print(f"Error importing book data: {e}")
            return False

    def _import_authors(self, conn: sqlite3.Connection, work_id: str, authors: List[Dict[str, Any]]) -> bool:
        """Import authors and author-book relationships"""
        try:
            now = datetime.now().isoformat()
            
            for author in authors:
                # Insert author
                author_data = {
                    'goodreads_id': author['goodreads_id'],
                    'name': author['name'],
                    'created_at': now,
                    'updated_at': now
                }
                
                fields = list(author_data.keys())
                placeholders = ','.join(['?'] * len(fields))
                values = [author_data[field] for field in fields]
                
                conn.execute(f"""
                    INSERT INTO author ({','.join(fields)})
                    VALUES ({placeholders})
                    ON CONFLICT(goodreads_id) DO UPDATE SET
                    {','.join(f"{field}=excluded.{field}" for field in fields if field != 'goodreads_id')}
                """, values)
                
                # Insert author-book relationship
                relation_data = {
                    'work_id': work_id,
                    'author_id': author['goodreads_id'],
                    'role': author['role'],
                    'created_at': now,
                    'updated_at': now
                }
                
                fields = list(relation_data.keys())
                placeholders = ','.join(['?'] * len(fields))
                values = [relation_data[field] for field in fields]
                
                conn.execute(f"""
                    INSERT INTO book_author ({','.join(fields)})
                    VALUES ({placeholders})
                    ON CONFLICT(work_id, author_id) DO UPDATE SET
                    {','.join(f"{field}=excluded.{field}" for field in fields if field not in ['work_id', 'author_id'])}
                """, values)
            
            return True
            
        except Exception as e:
            print(f"Error importing authors: {e}")
            return False

    def _import_series(self, conn: sqlite3.Connection, work_id: str, series_list: List[Dict[str, Any]]) -> bool:
        """Import series and book-series relationships"""
        try:
            now = datetime.now().isoformat()
            
            for series in series_list:
                if not series['goodreads_id']:
                    continue
                    
                # Insert series
                series_data = {
                    'goodreads_id': series['goodreads_id'],
                    'title': series['name'],
                    'created_at': now,
                    'updated_at': now
                }
                
                fields = list(series_data.keys())
                placeholders = ','.join(['?'] * len(fields))
                values = [series_data[field] for field in fields]
                
                conn.execute(f"""
                    INSERT INTO series ({','.join(fields)})
                    VALUES ({placeholders})
                    ON CONFLICT(goodreads_id) DO UPDATE SET
                    {','.join(f"{field}=excluded.{field}" for field in fields if field != 'goodreads_id')}
                """, values)
                
                # Insert book-series relationship
                relation_data = {
                    'work_id': work_id,
                    'series_id': series['goodreads_id'],
                    'series_order': series['order'],
                    'created_at': now,
                    'updated_at': now
                }
                
                fields = list(relation_data.keys())
                placeholders = ','.join(['?'] * len(fields))
                values = [relation_data[field] for field in fields]
                
                conn.execute(f"""
                    INSERT INTO book_series ({','.join(fields)})
                    VALUES ({placeholders})
                    ON CONFLICT(work_id, series_id) DO UPDATE SET
                    {','.join(f"{field}=excluded.{field}" for field in fields if field not in ['work_id', 'series_id'])}
                """, values)
            
            return True
            
        except Exception as e:
            print(f"Error importing series: {e}")
            return False

    def _import_genres(self, conn: sqlite3.Connection, work_id: str, genres: List[Dict[str, Any]]) -> bool:
        """Import genres and book-genre relationships"""
        try:
            now = datetime.now().isoformat()
            
            for genre in genres:
                # First ensure genre exists and get its ID
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
                
                # Insert book-genre relationship
                relation_data = {
                    'work_id': work_id,
                    'genre_id': genre_id,
                    'created_at': now,
                    'updated_at': now
                }
                
                fields = list(relation_data.keys())
                placeholders = ','.join(['?'] * len(fields))
                values = [relation_data[field] for field in fields]
                
                conn.execute(f"""
                    INSERT INTO book_genre ({','.join(fields)})
                    VALUES ({placeholders})
                    ON CONFLICT(work_id, genre_id) DO UPDATE SET
                    {','.join(f"{field}=excluded.{field}" for field in fields if field not in ['work_id', 'genre_id'])}
                """, values)
            
            return True
            
        except Exception as e:
            print(f"Error importing genres: {e}")
            return False