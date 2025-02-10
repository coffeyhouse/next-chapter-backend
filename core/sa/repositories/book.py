# core/sa/repositories/book.py
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import select, desc
from sqlalchemy.orm import Session, joinedload
from ..models import Book, Author, Genre, Series

class BookRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_goodreads_id(self, goodreads_id: str) -> Optional[Book]:
        """Get a book by its Goodreads ID"""
        return self.session.query(Book).filter(Book.goodreads_id == goodreads_id).first()

    def get_by_work_id(self, work_id: str) -> Optional[Book]:
        """Get a book by its work ID"""
        return self.session.query(Book).filter(Book.work_id == work_id).first()

    def search_books(self, query: str, limit: int = 20) -> List[Book]:
        """Search books by title and include author relationships.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            List of Book objects with loaded author relationships
        """
        base_query = self.session.query(Book).options(
            joinedload(Book.authors),
            joinedload(Book.genres),
            joinedload(Book.series)
        )
        
        if query and query.strip():
            base_query = base_query.filter(Book.title.ilike(f"%{query}%"))
        
        return base_query.order_by(desc(Book.goodreads_rating)).limit(limit).all()

    def get_books_by_author(self, author_id: str) -> List[Book]:
        """Get all books by a specific author"""
        return self.session.query(Book).join(
            Book.authors
        ).filter(
            Author.goodreads_id == author_id
        ).all()

    def get_books_by_genre(self, genre_name: str) -> List[Book]:
        """Get all books in a specific genre"""
        return self.session.query(Book).join(
            Book.genres
        ).filter(
            Genre.name == genre_name
        ).all()

    def get_books_with_rating_above(self, rating: float) -> List[Book]:
        """Get books with rating above specified threshold"""
        return self.session.query(Book).filter(
            Book.goodreads_rating >= rating
        ).order_by(
            desc(Book.goodreads_rating)
        ).all()

    def get_recent_books(self, limit: int = 10) -> List[Book]:
        """Get recently added books"""
        return self.session.query(Book).order_by(
            desc(Book.created_at)
        ).limit(limit).all()

    def get_books_in_series(self, series_id: str) -> List[Book]:
        """Get all books in a specific series"""
        return self.session.query(Book).join(
            Book.series
        ).filter(
            Series.goodreads_id == series_id
        ).all()

    def get_similar_books(self, work_id: str, limit: int = 10) -> List[Book]:
        """Get similar books for a given book"""
        book = self.session.query(Book).filter(Book.work_id == work_id).first()
        if not book:
            return []
        return book.similar_books[:limit]

    def get_books_with_filters(
        self,
        min_rating: Optional[float] = None,
        min_votes: Optional[int] = None,
        language: Optional[str] = None,
        limit: int = 50
    ) -> List[Book]:
        """Get books matching multiple filter criteria"""
        query = self.session.query(Book)
        
        if min_rating is not None:
            query = query.filter(Book.goodreads_rating >= min_rating)
        if min_votes is not None:
            query = query.filter(Book.goodreads_votes >= min_votes)
        if language is not None:
            query = query.filter(Book.language == language)
            
        return query.limit(limit).all()