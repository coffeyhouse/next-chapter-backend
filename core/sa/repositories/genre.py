# core/sa/repositories/genre.py

from typing import List, Optional
from sqlalchemy import func, desc
from sqlalchemy.orm import Session
from core.sa.models import Genre, Book

class GenreRepository:
    """Repository for managing Genre entities."""

    def __init__(self, session: Session):
        """Initialize the repository with a database session.
        
        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

    def get_by_name(self, name: str) -> Optional[Genre]:
        """Get a genre by its name.
        
        Args:
            name: The name of the genre to retrieve
            
        Returns:
            The Genre object if found, None otherwise
        """
        return self.session.query(Genre).filter(Genre.name == name).first()

    def search_genres(self, query: str, limit: int = 20) -> List[Genre]:
        """Search for genres by name.
        
        Args:
            query: The search query string
            limit: Maximum number of results to return (default: 20)
            
        Returns:
            List of matching Genre objects
        """
        base_query = self.session.query(Genre)
        if query:
            base_query = base_query.filter(Genre.name.ilike(f"%{query}%"))
        return base_query.limit(limit).all()

    def get_genres_by_book(self, goodreads_id: str) -> List[Genre]:
        """Get all genres associated with a specific book.
        
        Args:
            goodreads_id: The Goodreads ID of the book
            
        Returns:
            List of Genre objects associated with the book
        """
        book = self.session.query(Book).filter(Book.goodreads_id == goodreads_id).first()
        if not book:
            return []
        return book.genres

    def get_popular_genres(self, limit: int = 10) -> List[Genre]:
        """Get genres ordered by number of associated books.
        
        Args:
            limit: Maximum number of genres to return (default: 10)
            
        Returns:
            List of Genre objects ordered by popularity
        """
        return (self.session.query(Genre)
                .outerjoin(Genre.books)
                .group_by(Genre)
                .order_by(desc(func.count(Book.goodreads_id)))
                .limit(limit)
                .all())

    def get_recent_genres(self, limit: int = 10) -> List[Genre]:
        """Get recently added genres.
        
        Args:
            limit: Maximum number of genres to return (default: 10)
            
        Returns:
            List of Genre objects ordered by creation date
        """
        return (self.session.query(Genre)
                .order_by(desc(Genre.created_at))
                .limit(limit)
                .all())

    def merge_genres(self, source_name: str, target_name: str) -> Optional[Genre]:
        """Merge one genre into another.
        
        Args:
            source_name: Name of the genre to merge from
            target_name: Name of the genre to merge into
            
        Returns:
            The target Genre object if successful, None otherwise
        """
        source = self.get_by_name(source_name)
        target = self.get_by_name(target_name)

        if not source or not target:
            return None

        # Move all books from source to target
        for book in source.books:
            if book not in target.books:
                target.books.append(book)

        # Delete the source genre
        self.session.delete(source)
        self.session.commit()

        return target 