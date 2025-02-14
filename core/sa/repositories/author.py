# core/sa/repositories/author.py
from typing import Optional, List
from datetime import datetime, timedelta, UTC
from sqlalchemy import desc, func, or_, distinct
from sqlalchemy.orm import Session
from ..models import Author, Book, BookAuthor, BookUser

class AuthorRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_goodreads_id(self, goodreads_id: str) -> Optional[Author]:
        """Get an author by Goodreads ID"""
        return self.session.query(Author).filter(Author.goodreads_id == goodreads_id).first()

    def search_authors(self, query: str, limit: int = 20) -> List[Author]:
        """Search authors by name"""
        base_query = self.session.query(Author)
        if query:  # Only apply filter if query is not empty
            base_query = base_query.filter(Author.name.ilike(f"%{query}%"))
        return base_query.limit(limit).all()

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

    def get_unsynced_authors(self, days_old: int = 30, source: Optional[str] = None) -> List[Author]:
        """Get authors not synced within specified days, optionally filtered by book source
        
        Args:
            days_old: Number of days since last sync
            source: Optional source to filter by (e.g. 'library', 'series', 'read', 'top')
                   'read' will find authors of books that any user has read
                   'top' will find authors of highly voted books on Goodreads
            
        Returns:
            List of Author objects that need syncing
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=days_old)
        query = self.session.query(Author).filter(
            (Author.last_synced_at.is_(None)) | 
            (Author.last_synced_at < cutoff_date)
        )
        
        # If source is specified, only include authors who have books from that source
        if source:
            if source == 'read':
                # Find authors of books that any user has read
                query = (
                    query
                    .join(BookAuthor)
                    .join(Book)
                    .join(BookUser)
                    .filter(BookUser.status == 'completed')
                    .distinct()
                )
            elif source == 'top':
                # Find authors of highly voted books
                # Join with books and get max votes per author
                query = (
                    query
                    .join(BookAuthor)
                    .join(Book)
                    .filter(
                        Book.goodreads_votes.isnot(None),
                        Book.published_date >= '2000-01-01',  # Only books published after 2000
                        Book.published_date.isnot(None)  # Ensure we have a publication date
                    )
                    .group_by(Author.goodreads_id)
                    .having(func.max(Book.goodreads_votes) >= 10000)  # Minimum vote threshold
                    .order_by(desc(func.max(Book.goodreads_votes)))
                )
            else:
                query = query.join(BookAuthor).join(Book).filter(Book.source == source)
            
        query = query.order_by(Author.last_synced_at.asc().nullsfirst())
        
        authors = query.all()
        return [author for author in authors if author is not None]

    def get_prolific_authors(self, min_books: int = 5) -> List[Author]:
        """Get authors with at least the specified number of books"""
        return self.session.query(Author).join(
            Author.books
        ).group_by(
            Author.goodreads_id
        ).having(
            func.count(Book.goodreads_id) >= min_books
        ).all()