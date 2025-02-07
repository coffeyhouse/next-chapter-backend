# core/database/peewee_repositories/book_repository.py
from core.database.peewee_models import Book

class PeeweeBookRepository:
    def get_by_id(self, goodreads_id: str):
        return Book.get_or_none(Book.goodreads_id == goodreads_id)
    
    def search_books(self, query: str, limit: int = 20):
        return (Book
            .select()
            .where(
                (Book.title ** f"%{query}%") |
                (Book.goodreads_id ** f"%{query}%")
            )
            .limit(limit))