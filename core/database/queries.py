# core/database/queries.py
from typing import Dict, List, Any, Protocol
from datetime import datetime

class QueryExecutor(Protocol):
    def execute_query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        ...

class BaseQueries:
    def __init__(self, executor: QueryExecutor):
        self.execute_query = executor.execute_query

class BookQueries(BaseQueries):
    def get_all_books(
        self, 
        limit: int = 50, 
        offset: int = 0, 
        source: str = None,
        sort_by: str = "title",
        sort_order: str = "asc",
        include_library: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all books with flexible filtering and sorting options.
        
        Args:
            limit: Maximum number of books to return
            offset: Number of books to skip
            source: Filter by source (e.g. 'library', 'author', etc.)
            sort_by: Field to sort by ('title', 'published_date', 'goodreads_rating', 'goodreads_votes')
            sort_order: Sort direction ('asc' or 'desc')
            include_library: Whether to include library data (calibre_id, etc.)
            
        Returns:
            List of book records
        """
        # Validate sort parameters
        valid_sort_fields = {
            'title': 'b.title',
            'published_date': 'b.published_date',
            'goodreads_rating': 'b.goodreads_rating',
            'goodreads_votes': 'b.goodreads_votes',
            'created_at': 'b.created_at'
        }
        sort_field = valid_sort_fields.get(sort_by, 'b.title')
        sort_direction = 'DESC' if sort_order.lower() == 'desc' else 'ASC'
        
        # Build the base query
        if include_library:
            base_query = """
                SELECT b.*, l.calibre_id 
                FROM book b
                LEFT JOIN library l ON b.goodreads_id = l.goodreads_id
            """
        else:
            base_query = "SELECT b.* FROM book b"
        
        # Add source filter if specified
        where_clause = ""
        params = []
        if source:
            where_clause = "WHERE b.source = ?"
            params.append(source)
        
        # Add sorting and pagination
        query = f"""
            {base_query}
            {where_clause}
            ORDER BY {sort_field} {sort_direction} NULLS LAST
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        return self.execute_query(query, tuple(params))

    def get_unsynced_books(self, days_old: int = 30) -> List[Dict[str, Any]]:
        sql = """
            SELECT b.* FROM book b
            WHERE b.last_synced_at IS NULL
            OR datetime(b.last_synced_at) < datetime('now', ?)
            ORDER BY b.last_synced_at ASC NULLS FIRST
        """
        return self.execute_query(sql, (f'-{days_old} days',))

    def search_books(self, query: str) -> List[Dict[str, Any]]:
        sql = """
            SELECT * FROM book 
            WHERE title LIKE ?
            OR goodreads_id LIKE ?
            OR isbn LIKE ?
            LIMIT 20
        """
        search_param = f'%{query}%'
        return self.execute_query(sql, (search_param, search_param, search_param))

    def get_books_by_genre(self, genre_name: str) -> List[Dict[str, Any]]:
        sql = """
            SELECT b.* FROM book b
            JOIN book_genre bg ON b.work_id = bg.work_id
            JOIN genre g ON bg.genre_id = g.id
            WHERE g.name = ?
            ORDER BY b.goodreads_votes DESC NULLS LAST
        """
        return self.execute_query(sql, (genre_name,))

    def get_book_by_id(self, book_id: str) -> Dict[str, Any]:
        sql = """
            SELECT * FROM book 
            WHERE goodreads_id = ?
        """
        results = self.execute_query(sql, (book_id,))
        return results[0] if results else {}

    def get_similar_books(self, work_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        sql = """
            SELECT b.* FROM book b
            JOIN book_similar bs ON b.work_id = bs.similar_work_id
            WHERE bs.work_id = ?
            LIMIT ?
        """
        return self.execute_query(sql, (work_id, limit))

    def get_library_books(self) -> List[Dict[str, Any]]:
        sql = """
            SELECT b.*, l.calibre_id 
            FROM book b
            JOIN library l ON b.goodreads_id = l.goodreads_id
            ORDER BY b.title
        """
        return self.execute_query(sql)

class AuthorQueries(BaseQueries):
    def get_unsynced_authors(self, days_old: int = 30, source: str = None) -> List[Dict[str, Any]]:
        if source:
            sql = """
                SELECT DISTINCT a.* FROM author a
                JOIN book_author ba ON a.goodreads_id = ba.author_id
                JOIN book b ON b.work_id = ba.work_id
                WHERE ba.role = 'Author'
                AND b.source = ?
                AND (a.last_synced_at IS NULL
                OR datetime(a.last_synced_at) < datetime('now', ?))
                ORDER BY a.last_synced_at ASC NULLS FIRST
            """
            return self.execute_query(sql, (source, f'-{days_old} days'))
        else:
            sql = """
                SELECT DISTINCT a.* FROM author a
                JOIN book_author ba ON a.goodreads_id = ba.author_id
                WHERE ba.role = 'Author'
                AND (a.last_synced_at IS NULL
                OR datetime(a.last_synced_at) < datetime('now', ?))
                ORDER BY a.last_synced_at ASC NULLS FIRST
            """
            return self.execute_query(sql, (f'-{days_old} days',))

    def get_books_by_author(self, author_id: str) -> List[Dict[str, Any]]:
        sql = """
            SELECT b.* FROM book b
            JOIN book_author ba ON b.work_id = ba.work_id
            WHERE ba.author_id = ?
            ORDER BY b.published_date ASC NULLS LAST
        """
        return self.execute_query(sql, (author_id,))

    def get_author_by_id(self, author_id: str) -> Dict[str, Any]:
        sql = """
            SELECT * FROM author
            WHERE goodreads_id = ?
        """
        results = self.execute_query(sql, (author_id,))
        return results[0] if results else {}

    def search_authors(self, query: str) -> List[Dict[str, Any]]:
        sql = """
            SELECT * FROM author
            WHERE name LIKE ?
            LIMIT 20
        """
        return self.execute_query(sql, (f'%{query}%',))

class SeriesQueries(BaseQueries):
    def get_unsynced_series(self, days_old: int = 30, source: str = None) -> List[Dict[str, Any]]:
        if source:
            sql = """
                SELECT DISTINCT s.* FROM series s
                JOIN book_series bs ON s.goodreads_id = bs.series_id
                JOIN book b ON b.work_id = bs.work_id
                WHERE b.source = ?
                AND (s.last_synced_at IS NULL
                OR datetime(s.last_synced_at) < datetime('now', ?))
                ORDER BY s.last_synced_at ASC NULLS FIRST
            """
            return self.execute_query(sql, (source, f'-{days_old} days'))
        else:
            sql = """
                SELECT s.* FROM series s
                WHERE s.last_synced_at IS NULL
                OR datetime(s.last_synced_at) < datetime('now', ?)
                ORDER BY s.last_synced_at ASC NULLS FIRST
            """
            return self.execute_query(sql, (f'-{days_old} days',))

    def get_books_in_series(self, series_id: str) -> List[Dict[str, Any]]:
        sql = """
            SELECT b.*, bs.series_order FROM book b
            JOIN book_series bs ON b.work_id = bs.work_id
            WHERE bs.series_id = ?
            ORDER BY bs.series_order ASC NULLS LAST
        """
        return self.execute_query(sql, (series_id,))

    def get_series_by_id(self, series_id: str) -> Dict[str, Any]:
        sql = """
            SELECT * FROM series
            WHERE goodreads_id = ?
        """
        results = self.execute_query(sql, (series_id,))
        return results[0] if results else {}

    def search_series(self, query: str) -> List[Dict[str, Any]]:
        sql = """
            SELECT * FROM series
            WHERE title LIKE ?
            LIMIT 20
        """
        return self.execute_query(sql, (f'%{query}%',))

class StatsQueries(BaseQueries):
    def get_library_stats(self) -> Dict[str, int]:
        sql = """
            SELECT 
                (SELECT COUNT(*) FROM book) as total_books,
                (SELECT COUNT(*) FROM author) as total_authors,
                (SELECT COUNT(*) FROM series) as total_series,
                (SELECT COUNT(*) FROM genre) as total_genres,
                (SELECT COUNT(*) FROM library) as library_books
        """
        results = self.execute_query(sql)
        return results[0] if results else {}

    def get_genre_stats(self) -> List[Dict[str, Any]]:
        sql = """
            SELECT g.name, COUNT(*) as book_count
            FROM genre g
            JOIN book_genre bg ON g.id = bg.genre_id
            GROUP BY g.name
            ORDER BY book_count DESC
        """
        return self.execute_query(sql)