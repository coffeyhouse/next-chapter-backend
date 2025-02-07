# core/services/book_service.py

from typing import List, Optional
from datetime import datetime
from fastapi import HTTPException

from core.models.book import (
    BookDetail, BookListItem, SimilarBook,
    ReadingStatus, UpdateReadingStatus, UpdateWantedStatus
)
from core.database import GoodreadsDB
from core.database.queries import BookQueries

class BookService:
    def __init__(self, db: GoodreadsDB):
        self.db = db
        self.queries = BookQueries(db)

    async def get_book_detail(self, goodreads_id: str, user_id: Optional[int] = None) -> BookDetail:
        """Get detailed book information including all relationships"""
        # Get base book data
        book_data = self.db.get_by_id('book', goodreads_id, id_field='goodreads_id')
        if not book_data:
            raise HTTPException(status_code=404, detail="Book not found")

        # Get user-specific data if user_id provided
        reading_status = ReadingStatus.NONE
        is_wanted = False
        if user_id:
            user_book = self.db.execute_query("""
                SELECT status, wanted 
                FROM book_user 
                WHERE work_id = ? AND user_id = ?
            """, (book_data['work_id'], user_id))
            if user_book:
                reading_status = ReadingStatus(user_book[0]['status'])
                is_wanted = user_book[0].get('wanted', False)

        # Check library status
        library_data = self.db.execute_query("""
            SELECT calibre_id as library_calibre_id
            FROM library
            WHERE work_id = ?
        """, (book_data['work_id'],))
        is_in_library = bool(library_data)
        calibre_id = library_data[0]['library_calibre_id'] if library_data else None

        # Get authors
        authors = self.db.execute_query("""
            SELECT a.goodreads_id, a.name, ba.role
            FROM author a
            JOIN book_author ba ON a.goodreads_id = ba.author_id
            WHERE ba.work_id = ?
        """, (book_data['work_id'],))

        # Get series
        series = self.db.execute_query("""
            SELECT s.goodreads_id, s.title, bs.series_order as "order"
            FROM series s
            JOIN book_series bs ON s.goodreads_id = bs.series_id
            WHERE bs.work_id = ?
            ORDER BY bs.series_order ASC NULLS LAST
        """, (book_data['work_id'],))

        # Get genres
        genres = self.db.execute_query("""
            SELECT g.name
            FROM genre g
            JOIN book_genre bg ON g.id = bg.genre_id
            WHERE bg.work_id = ?
        """, (book_data['work_id'],))

        # Get similar books
        similar_books = await self.get_similar_books(book_data['work_id'])

        # Combine all data into BookDetail model
        return BookDetail(
            **book_data,
            authors=authors,
            series=series,
            genres=genres,
            similar_books=similar_books,
            reading_status=reading_status,
            is_wanted=is_wanted,
            is_in_library=is_in_library,
            library_calibre_id=calibre_id
        )

    async def get_similar_books(self, work_id: str, limit: int = 5) -> List[SimilarBook]:
        """Get similar books with their authors"""
        similar = self.db.execute_query("""
            SELECT b.*, a.goodreads_id as author_id, a.name as author_name, 
                   ba.role as author_role
            FROM book b
            JOIN book_similar bs ON b.work_id = bs.similar_work_id
            JOIN book_author ba ON b.work_id = ba.work_id
            JOIN author a ON ba.author_id = a.goodreads_id
            WHERE bs.work_id = ?
            LIMIT ?
        """, (work_id, limit))

        # Group by book and collect authors
        books_dict = {}
        for row in similar:
            if row['work_id'] not in books_dict:
                books_dict[row['work_id']] = {
                    **row,
                    'authors': []
                }
            books_dict[row['work_id']]['authors'].append({
                'goodreads_id': row['author_id'],
                'name': row['author_name'],
                'role': row['author_role']
            })

        return [SimilarBook(**book_data) for book_data in books_dict.values()]

    async def update_reading_status(self, 
        goodreads_id: str, 
        update: UpdateReadingStatus
    ) -> BookDetail:
        """Update a book's reading status for a user"""
        book = self.db.get_by_id('book', goodreads_id, id_field='goodreads_id')
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        # Update book_user table
        now = datetime.now().isoformat()
        self.db.execute_query("""
            INSERT INTO book_user (work_id, user_id, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(work_id, user_id) DO UPDATE SET
                status = excluded.status,
                updated_at = excluded.updated_at
        """, (book['work_id'], update.user_id, update.status.value, now, now))

        # Return updated book detail
        return await self.get_book_detail(goodreads_id, update.user_id)

    async def update_wanted_status(self, 
        goodreads_id: str, 
        update: UpdateWantedStatus
    ) -> BookDetail:
        """Update a book's wanted status for a user"""
        book = self.db.get_by_id('book', goodreads_id, id_field='goodreads_id')
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        # Update book_user table
        now = datetime.now().isoformat()
        self.db.execute_query("""
            INSERT INTO book_user (work_id, user_id, wanted, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(work_id, user_id) DO UPDATE SET
                wanted = excluded.wanted,
                updated_at = excluded.updated_at
        """, (book['work_id'], update.user_id, update.is_wanted, now, now))

        # Return updated book detail
        return await self.get_book_detail(goodreads_id, update.user_id)

    async def search_books(self, 
        query: str, 
        user_id: Optional[int] = None
    ) -> List[BookListItem]:
        """Search books and include user-specific data"""
        books = self.queries.search_books(query)
        
        # Return empty list if no books found
        if not books:
            return []
            
        # If no user_id, return basic book data
        if not user_id:
            return [BookListItem(**book) for book in books]

        # Get user data for these books
        book_ids = [book['work_id'] for book in books]
        user_data = self.db.execute_query("""
            SELECT work_id, status, wanted
            FROM book_user
            WHERE work_id IN ({})
            AND user_id = ?
        """.format(','.join('?' * len(book_ids))), (*book_ids, user_id))

        # Create lookup of user data by work_id
        user_data_map = {
            d['work_id']: {
                'status': d['status'],
                'wanted': d['wanted']
            } for d in user_data
        }

        # Combine book and user data
        return [
            BookListItem(
                **book,
                reading_status=ReadingStatus(
                    user_data_map.get(book['work_id'], {}).get('status', 'none')
                ),
                is_wanted=user_data_map.get(book['work_id'], {}).get('wanted', False)
            )
            for book in books
        ]

    async def get_all_books(
        self,
        limit: int = 50,
        offset: int = 0,
        source: Optional[str] = None,
        sort_by: str = "title",
        sort_order: str = "asc",
        user_id: Optional[int] = None
    ) -> List[BookListItem]:
        """Get all books with pagination and optional user data"""
        # Get base book data using the query class
        books = self.queries.get_all_books(
            limit=limit,
            offset=offset,
            source=source,
            sort_by=sort_by,
            sort_order=sort_order,
            include_library=True
        )
        
        # Return empty list if no books found
        if not books:
            return []
            
        # Get book IDs for relationship queries
        book_ids = [book['work_id'] for book in books]
        
        # Get authors for all books
        authors = self.db.execute_query("""
            SELECT ba.work_id, a.goodreads_id, a.name, ba.role
            FROM book_author ba
            JOIN author a ON ba.author_id = a.goodreads_id
            WHERE ba.work_id IN ({})
        """.format(','.join('?' * len(book_ids))), book_ids)

        # Group authors by work_id
        author_map = {}
        for author in authors:
            if author['work_id'] not in author_map:
                author_map[author['work_id']] = []
            author_map[author['work_id']].append({
                'goodreads_id': author['goodreads_id'],
                'name': author['name'],
                'role': author['role']
            })

        # Get primary series for all books
        series = self.db.execute_query("""
            SELECT bs.work_id, s.goodreads_id, s.title, bs.series_order as "order"
            FROM book_series bs
            JOIN series s ON bs.series_id = s.goodreads_id
            WHERE bs.work_id IN ({})
            ORDER BY bs.series_order ASC NULLS LAST
        """.format(','.join('?' * len(book_ids))), book_ids)

        # Create lookup of primary series by work_id
        series_map = {
            s['work_id']: {
                'goodreads_id': s['goodreads_id'],
                'title': s['title'],
                'order': s['order']
            } for s in series
        }

        # If no user_id, return book data with relationships but no user-specific data
        if not user_id:
            return [
                BookListItem(
                    **book,
                    authors=author_map.get(book['work_id'], []),
                    series=series_map.get(book['work_id']),
                    reading_status=ReadingStatus.NONE,
                    is_wanted=False,
                    is_in_library=bool(book.get('calibre_id'))
                )
                for book in books
            ]

        # Get user data for these books
        user_data = self.db.execute_query("""
            SELECT work_id, status, wanted
            FROM book_user
            WHERE work_id IN ({})
            AND user_id = ?
        """.format(','.join('?' * len(book_ids))), (*book_ids, user_id))

        # Create lookup of user data by work_id
        user_data_map = {
            d['work_id']: {
                'status': d['status'],
                'wanted': d['wanted']
            } for d in user_data
        }

        # Combine all data into BookListItem models
        return [
            BookListItem(
                **book,
                authors=author_map.get(book['work_id'], []),
                series=series_map.get(book['work_id']),
                reading_status=ReadingStatus(
                    user_data_map.get(book['work_id'], {}).get('status', 'none')
                ),
                is_wanted=user_data_map.get(book['work_id'], {}).get('wanted', False),
                is_in_library=bool(book.get('calibre_id'))
            )
            for book in books
        ]