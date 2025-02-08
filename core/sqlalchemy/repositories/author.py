# core/sqlalchemy/repositories/author.py
from typing import Optional, List
from datetime import datetime, timedelta, UTC
from sqlalchemy import desc, func
from sqlalchemy.orm import Session
from ..models import Author, Book

class AuthorRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_goodreads_id(self, goodreads_id: str) -> Optional[Author]:
        """Get an author by Goodreads ID"""
        return self.session.query(Author).filter(Author.goodreads_id == goodreads_id).first()

    def search_authors(self, query: str, limit: int = 20) -> List[Author]:
        """Search authors by name"""
        return self.session.query(Author).filter(
            Author.name.ilike(f"%{query}%")
        ).limit(limit).all()

    def get_recent_authors(self, limit: int = 10) -> List[Author]:
        """Get recently added authors"""
        return self.session.query(Author).order_by(
            desc(Author.created_at)
        ).limit(limit).all()

    def get_authors_by_book(self, book_id: str) -> List[Author]:
        """Get all authors for a specific book"""
        return self.session.query(Author).join(
            Author.books
        ).filter(
            Book.goodreads_id == book_id
        ).all()

    def get_unsynced_authors(self, days_old: int = 30) -> List[Author]:
        """Get authors not synced within specified days"""
        cutoff_date = datetime.now(UTC) - timedelta(days=days_old)
        return self.session.query(Author).filter(
            (Author.last_synced_at.is_(None)) | 
            (Author.last_synced_at < cutoff_date)
        ).order_by(Author.last_synced_at.asc().nullsfirst()).all()

    def get_prolific_authors(self, min_books: int = 5) -> List[Author]:
        """Get authors with at least the specified number of books"""
        return self.session.query(Author).join(
            Author.books
        ).group_by(
            Author.goodreads_id
        ).having(
            func.count(Book.goodreads_id) >= min_books
        ).all()