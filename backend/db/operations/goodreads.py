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
        """Update book information"""
        now = datetime.now().isoformat()
        book_data.update({
            'updated_at': now,
            'last_synced_at': now
        })
        return self.upsert('books', book_data, 'goodreads_id')

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
        now = datetime.now().isoformat()
        author_data.update({
            'updated_at': now,
            'last_synced_at': now
        })
        return self.upsert('authors', author_data, 'goodreads_id')

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