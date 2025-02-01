# backend/db/operations/goodreads.py
import sqlite3
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
from pathlib import Path

from .base import BaseDBOperations

logger = logging.getLogger(__name__)

class GoodreadsDB(BaseDBOperations):
    """Goodreads-specific database operations"""
    
    def __init__(self, db_path: str = "books.db"):
        super().__init__(db_path)
        self._ensure_db_exists()
        
    def _ensure_db_exists(self):
        """Create database and tables if they don't exist"""
        if not Path(self.db_path).exists():
            from backend.db.db_init import init_db
            init_db(self.db_path)

    # Book operations
    def update_book(self, book_data: Dict[str, Any]) -> bool:
        """Update book information and all relationships"""
        valid_fields = {
            'goodreads_id', 'title', 'published_date', 'published_state',
            'language', 'calibre_id', 'pages', 'isbn', 'goodreads_rating',
            'goodreads_votes', 'description', 'image_url', 'similar_books_id',
            'source', 'hidden',
            # Add timestamp fields
            'created_at', 'updated_at', 'last_synced_at'
        }
        
        clean_data = {
            k: v for k, v in book_data.items() 
            if k in valid_fields
        }
        
        # Add some debug output
        print("\nData after cleaning in update_book:")
        print(f"Fields present: {list(clean_data.keys())}")
        print(f"Created at: {clean_data.get('created_at', 'MISSING')}")
        
        # Try to update book data first
        success, _ = self.upsert('books', clean_data, 'goodreads_id')
        if not success:
            return False
            
        # Update relationships
        if not self.update_book_relationships(book_data):
            return False
        
        # Since we now include timestamps in valid_fields, we don't need a separate
        # update for last_synced_at - it's already handled in the main update
        
        return True

    def get_books_by_author(self, author_id: str) -> List[Dict[str, Any]]:
        """Get all books by an author"""
        sql = """
            SELECT b.* 
            FROM books b
            JOIN author_books ab ON b.goodreads_id = ab.book_id
            WHERE ab.author_id = ?
            ORDER BY b.title
        """
        return self.execute_query(sql, (author_id,))

    def get_unsynced_books(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get books that haven't been synced"""
        return self.get_all(
            table='books',
            conditions={'last_synced_at': None},
            order_by='title',
            limit=limit
        )

    # Author operations
    def update_author(self, author_data: Dict[str, Any]) -> bool:
        """Update author information"""
        valid_fields = {
            'goodreads_id', 'name', 'bio', 'image_url'
        }
        
        clean_data = {
            k: v for k, v in author_data.items() 
            if k in valid_fields
        }
        
        # Try to update author data first
        success, _ = self.upsert('authors', clean_data, 'goodreads_id')
        
        # Only update last_synced_at if the operation succeeded
        if success:
            sync_success, _ = self.upsert('authors', {
                'goodreads_id': clean_data['goodreads_id'],
                'last_synced_at': datetime.now().isoformat()
            }, 'goodreads_id')
            return sync_success
            
        return success

    def get_unsynced_authors(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get authors that haven't been synced"""
        return self.get_all(
            table='authors',
            conditions={'last_synced_at': None},
            order_by='name',
            limit=limit
        )

    # Series operations
    def update_series(self, series_data: Dict[str, Any]) -> bool:
        """Update series information"""
        now = datetime.now().isoformat()
        series_data.update({
            'updated_at': now,
            'last_synced_at': now
        })
        return self.upsert('series', series_data, 'goodreads_id')

    def get_unsynced_series(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get series that haven't been synced"""
        return self.get_all(
            table='series',
            conditions={'last_synced_at': None},
            order_by='title',
            limit=limit
        )

    # Relationship operations
    def add_book_author(self, book_id: str, author_id: str, role: str = "Author") -> bool:
        """Add book-author relationship"""
        now = datetime.now().isoformat()
        return self.upsert(
            'author_books',
            {
                'book_id': book_id,
                'author_id': author_id,
                'role': role,
                'created_at': now,
                'updated_at': now
            },
            'book_id'
        )

    def add_book_series(
        self, 
        book_id: str, 
        series_id: str, 
        series_order: Optional[float] = None
    ) -> bool:
        """Add book-series relationship"""
        now = datetime.now().isoformat()
        return self.upsert(
            'book_series',
            {
                'book_id': book_id,
                'series_id': series_id,
                'series_order': series_order,
                'created_at': now,
                'updated_at': now
            },
            'book_id'
        )

    # Stats and utilities
    def get_stats(self) -> Dict[str, int]:
        """Get record counts for all tables"""
        stats = {}
        tables = self.execute_query("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)
        
        for table in tables:
            count = self.execute_query(f"SELECT COUNT(*) as count FROM {table['name']}")
            stats[table['name']] = count[0]['count']
            
        return stats

    def get_recent_updates(self, days: int = 7) -> Dict[str, List[Dict[str, Any]]]:
        """Get recently updated records"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        updates = {
            'books': self.execute_query(
                "SELECT * FROM books WHERE updated_at > ? ORDER BY updated_at DESC LIMIT 10",
                (cutoff,)
            ),
            'authors': self.execute_query(
                "SELECT * FROM authors WHERE updated_at > ? ORDER BY updated_at DESC LIMIT 10",
                (cutoff,)
            ),
            'series': self.execute_query(
                "SELECT * FROM series WHERE updated_at > ? ORDER BY updated_at DESC LIMIT 10",
                (cutoff,)
            )
        }
        
        return updates
    
    def update_book_relationships(self, book_data: Dict[str, Any]) -> bool:
        """Update all relationships for a book"""
        book_id = book_data['goodreads_id']
        success = True
        now = datetime.now().isoformat()
        
        # Process authors
        if 'authors' in book_data:
            try:
                # First remove existing relationships
                with self._get_connection() as conn:
                    conn.execute(
                        "DELETE FROM author_books WHERE book_id = ?",
                        (book_id,)
                    )
                
                # Add new relationships
                for author in book_data['authors']:
                    # First ensure author exists
                    author_data = {
                        'goodreads_id': author['id'],
                        'name': author['name'],
                        'created_at': now,
                        'updated_at': now
                    }
                    self.upsert('authors', author_data, 'goodreads_id')
                    
                    # Then add relationship
                    relationship = {
                        'book_id': book_id,
                        'author_id': author['id'],
                        'role': author.get('role', 'Author'),
                        'created_at': now,
                        'updated_at': now
                    }
                    
                    success, _ = self.upsert(
                        'author_books',
                        relationship,
                        ['book_id', 'author_id']  # Pass as list instead of string
                    )
                    if not success:
                        return False
                        
            except Exception as e:
                logger.error(f"Error processing authors: {str(e)}")
                return False

        # Process series - now using the flattened structure
        if 'series' in book_data:
            try:
                # Remove existing relationships
                with self._get_connection() as conn:
                    conn.execute(
                        "DELETE FROM book_series WHERE book_id = ?",
                        (book_id,)
                    )
                
                # Add each series relationship
                for series in book_data['series']:
                    # First ensure series exists
                    series_data = {
                        'goodreads_id': series['id'],
                        'title': series['name'],
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    }
                    self.upsert('series', series_data, 'goodreads_id')
                    
                    # Then add relationship
                    relationship = {
                        'book_id': book_id,
                        'series_id': series['id'],
                        'series_order': series.get('order'),
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    }
                    success, _ = self.upsert(
                        'book_series',
                        relationship,
                        'book_id, series_id'  # Composite key
                    )
                    if not success:
                        return False
                        
            except Exception as e:
                logger.error(f"Error processing series: {str(e)}")
                return False

        # Process genres
        if 'genres' in book_data:
            try:
                # Remove existing relationships
                with self._get_connection() as conn:
                    conn.execute(
                        "DELETE FROM book_genres WHERE book_id = ?",
                        (book_id,)
                    )
                
                for genre in book_data['genres']:
                    if not self.update_book_genre(book_id, genre['name']):
                        success = False
                        
            except Exception as e:
                logger.error(f"Error processing genres: {str(e)}")
                return False

        return success

    def update_book_author(self, book_id: str, author_data: Dict[str, Any]) -> bool:
        """Update book-author relationship and ensure author exists
        
        Args:
            book_id: Goodreads book ID
            author_data: Author data including id, name, and role
            
        Returns:
            bool: True if successful
        """
        # First ensure author exists
        author = {
            'goodreads_id': author_data['id'],
            'name': author_data['name']
        }
        success, _ = self.upsert('authors', author, 'goodreads_id')
        if not success:
            return False

        # Then add relationship
        relationship = {
            'book_id': book_id,
            'author_id': author_data['id'],
            'role': author_data.get('role', 'Author')
        }
        success, _ = self.upsert(
            'author_books', 
            relationship,
            'book_id'  # Assuming book_id is primary key in relationship table
        )
        return success

    def update_book_series(
        self, 
        book_id: str, 
        series_id: str, 
        series_order: Optional[float] = None
    ) -> bool:
        """Update book-series relationship and ensure series exists
        
        Args:
            book_id: Goodreads book ID
            series_id: Goodreads series ID
            series_order: Optional book number in series
            
        Returns:
            bool: True if successful
        """
        # Add relationship
        relationship = {
            'book_id': book_id,
            'series_id': series_id,
            'series_order': series_order
        }
        success, _ = self.upsert(
            'book_series', 
            relationship,
            'book_id'
        )
        return success

    def update_book_genre(self, book_id: str, genre_name: str) -> bool:
        """Update book-genre relationship and ensure genre exists"""
        try:
            now = datetime.now().isoformat()  # Get timestamp once for consistency
            
            with self._get_connection() as conn:
                # First get or create genre
                cursor = conn.execute(
                    "SELECT id FROM genres WHERE name = ?",
                    (genre_name,)
                )
                result = cursor.fetchone()
                
                if result:
                    genre_id = result[0]
                else:
                    # Get next available ID for new genre
                    cursor = conn.execute(
                        "SELECT COALESCE(MAX(id), 0) + 1 FROM genres"
                    )
                    genre_id = cursor.fetchone()[0]
                    
                    # Insert new genre with timestamps
                    conn.execute(
                        """
                        INSERT INTO genres (id, name, created_at, updated_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (genre_id, genre_name, now, now)
                    )
                
                # Add relationship with timestamps
                relationship = {
                    'book_id': book_id,
                    'genre_id': genre_id,
                    'created_at': now,
                    'updated_at': now
                }
                
                # Use upsert for the relationship
                success, _ = self.upsert(
                    'book_genres',
                    relationship,
                    ['book_id', 'genre_id']
                )
                return success
                
        except Exception as e:
            logger.error(f"Error updating book genre: {str(e)}")
            return False