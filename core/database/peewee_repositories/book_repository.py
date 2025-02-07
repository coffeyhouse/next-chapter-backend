# core/database/peewee_repositories/book_repository.py
from typing import List, Optional
from core.database.peewee_models import Book, Author, BookAuthor

class PeeweeBookRepository:
    def get_by_id(self, goodreads_id: str) -> Optional[Book]:
        return Book.get_or_none(Book.goodreads_id == goodreads_id)
    
    def search_books(self, query: str, limit: int = 20) -> List[Book]:
        return list(Book
            .select()
            .where(
                (Book.title ** f"%{query}%") |
                (Book.goodreads_id ** f"%{query}%")
            )
            .limit(limit))
    
    def get_with_authors(self, goodreads_id: str) -> Optional[Book]:
        return (Book
            .select(Book, Author)
            .join(BookAuthor)
            .join(Author)
            .where(Book.goodreads_id == goodreads_id)
            .first())