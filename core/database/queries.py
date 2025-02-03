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
            ORDER BY b.goodreads_rating DESC NULLS LAST
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
    def get_unsynced_authors(self, days_old: int = 30) -> List[Dict[str, Any]]:
        sql = """
            SELECT a.* FROM author a
            WHERE a.last_synced_at IS NULL
            OR datetime(a.last_synced_at) < datetime('now', ?)
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
    def get_unsynced_series(self, days_old: int = 30) -> List[Dict[str, Any]]:
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