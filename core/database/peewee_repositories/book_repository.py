# core/database/peewee_repositories/book_repository.py
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from peewee import JOIN, fn
from .base_repository import BaseRepository
from core.database.peewee_models import (
    Book, Author, Series, Genre,
    BookAuthor, BookSeries, BookGenre, BookUser, Library
)

class BookRepository(BaseRepository):
    def __init__(self):
        super().__init__(Book)

    def get_by_id(self, goodreads_id: str) -> Optional[Book]:
        """Get a book by its Goodreads ID"""
        return Book.get_or_none(Book.goodreads_id == goodreads_id)

    def get_with_relationships(self, goodreads_id: str) -> Optional[Book]:
        """Get a book with all its relationships loaded"""
        return (Book
            .select(Book, Author, Series, Genre)
            .join(BookAuthor, JOIN.LEFT_OUTER)
            .join(Author, JOIN.LEFT_OUTER)
            .switch(Book)
            .join(BookSeries, JOIN.LEFT_OUTER)
            .join(Series, JOIN.LEFT_OUTER)
            .switch(Book)
            .join(BookGenre, JOIN.LEFT_OUTER)
            .join(Genre, JOIN.LEFT_OUTER)
            .where(Book.goodreads_id == goodreads_id)
            .first())

    def search_books(self, query: str) -> List[Book]:
        """Search books by title or ISBN"""
        return (Book
            .select()
            .where(
                (Book.title.contains(query)) |
                (Book.isbn.contains(query))
            )
            .order_by(Book.title)
            .limit(20))

    def get_books_by_genre(self, genre_name: str) -> List[Book]:
        """Get all books in a specific genre"""
        return (Book
            .select()
            .join(BookGenre)
            .join(Genre)
            .where(Genre.name == genre_name)
            .order_by(Book.goodreads_votes.desc(nulls='LAST')))

    def get_library_books(self) -> List[Book]:
        """Get all books that are in the library"""
        return (Book
            .select()
            .join(Library)
            .order_by(Book.title))

    def get_unsynced_books(self, days: int = 30) -> List[Book]:
        """Get books that haven't been synced in the specified number of days"""
        cutoff = datetime.now() - timedelta(days=days)
        return (Book
            .select()
            .where(
                (Book.last_synced_at.is_null()) |
                (Book.last_synced_at < cutoff)
            )
            .order_by(Book.last_synced_at.asc(nulls='FIRST')))

    def update_book(self, goodreads_id: str, data: Dict[str, Any]) -> Optional[Book]:
        """Update a book's details"""
        book = self.get_by_id(goodreads_id)
        if not book:
            return None

        for key, value in data.items():
            setattr(book, key, value)
        book.updated_at = datetime.now()
        book.save()
        return book

    def update_reading_status(self, work_id: str, user_id: int, status: str) -> bool:
        """Update a user's reading status for a book"""
        try:
            BookUser.insert(
                work_id=work_id,
                user_id=user_id,
                status=status,
                created_at=datetime.now(),
                updated_at=datetime.now()
            ).on_conflict(
                conflict_target=[BookUser.work_id, BookUser.user_id],
                update={
                    BookUser.status: status,
                    BookUser.updated_at: datetime.now()
                }
            ).execute()
            return True
        except Exception as e:
            print(f"Error updating reading status: {e}")
            return False

    def upsert_book(self, data: Dict[str, Any]) -> Optional[Book]:
        """Insert or update a book"""
        try:
            book = Book.get_or_none(Book.goodreads_id == data['goodreads_id'])
            if book:
                # Update existing book
                for key, value in data.items():
                    setattr(book, key, value)
                book.updated_at = datetime.now()
                book.save()
            else:
                # Create new book
                data['created_at'] = datetime.now()
                data['updated_at'] = datetime.now()
                book = Book.create(**data)
            return book
        except Exception as e:
            print(f"Error upserting book: {e}")
            return None    