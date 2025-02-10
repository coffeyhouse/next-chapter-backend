from typing import List, Optional
from datetime import datetime, timedelta, UTC
from sqlalchemy import func, desc
from sqlalchemy.orm import Session, joinedload
from core.sa.models import User, Book, BookUser

class UserRepository:
    """Repository for managing User entities."""

    def __init__(self, session: Session):
        """Initialize the repository with a database session.
        
        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get a user by their ID.
        
        Args:
            user_id: The ID of the user to retrieve
            
        Returns:
            The User object if found, None otherwise
        """
        return self.session.query(User).filter(User.id == user_id).first()

    def search_users(self, query: str, limit: int = 20) -> List[User]:
        """Search for users by name.
        
        Args:
            query: The search query string
            limit: Maximum number of results to return (default: 20)
            
        Returns:
            List of matching User objects
        """
        base_query = self.session.query(User)
        if query:
            base_query = base_query.filter(User.name.ilike(f"%{query}%"))
        return base_query.limit(limit).all()

    def get_users_by_book(self, goodreads_id: str) -> List[User]:
        """Get all users who have a relationship with a specific book.
        
        Args:
            goodreads_id: The Goodreads ID of the book
            
        Returns:
            List of User objects associated with the book
        """
        return (
            self.session.query(User)
            .join(User.book_users)
            .join(BookUser.book)
            .filter(Book.goodreads_id == goodreads_id)
            .all()
        )

    def get_users_by_book_status(self, status: str, limit: int = 20) -> List[User]:
        """Get users who have books with a specific status.
        
        Args:
            status: The book status to filter by (e.g., 'reading', 'completed')
            limit: Maximum number of users to return (default: 20)
            
        Returns:
            List of User objects with books in the specified status
        """
        return (
            self.session.query(User)
            .join(User.book_users)
            .filter(BookUser.status == status)
            .group_by(User)
            .limit(limit)
            .all()
        )

    def get_active_readers(self, days: int = 30, limit: int = 20) -> List[User]:
        """Get users who have recently updated their book statuses.
        
        Args:
            days: Number of days to look back (default: 30)
            limit: Maximum number of users to return (default: 20)
            
        Returns:
            List of User objects ordered by recent activity
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=days)
        return (
            self.session.query(User)
            .join(User.book_users)
            .filter(BookUser.updated_at >= cutoff_date)
            .group_by(User)
            .order_by(desc(func.max(BookUser.updated_at)))
            .limit(limit)
            .all()
        )

    def get_user_with_books(self, user_id: int) -> Optional[User]:
        """Get a user along with their book relationships.
        
        Args:
            user_id: The ID of the user to retrieve
            
        Returns:
            The User object with loaded book relationships if found, None otherwise
        """
        return (
            self.session.query(User)
            .options(
                joinedload(User.book_users)
                .joinedload(BookUser.book)
            )
            .filter(User.id == user_id)
            .first()
        )

    def update_book_status(
        self, 
        user_id: int, 
        goodreads_id: str, 
        status: str,
        source: Optional[str] = None,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None
    ) -> Optional[BookUser]:
        """Update or create a user's status for a book.
        
        Args:
            user_id: The ID of the user
            goodreads_id: The Goodreads ID of the book
            status: The new status to set
            source: Optional source of the status update
            started_at: Optional start date
            finished_at: Optional finish date
            
        Returns:
            The updated or created BookUser object if successful, None otherwise
        """
        # Get the book's work_id
        book = self.session.query(Book).filter(Book.goodreads_id == goodreads_id).first()
        if not book:
            return None

        # Find existing book-user relationship or create new one
        book_user = (
            self.session.query(BookUser)
            .filter(
                BookUser.user_id == user_id,
                BookUser.work_id == book.work_id
            )
            .first()
        )

        if book_user:
            # Update existing relationship
            book_user.status = status
            book_user.source = source
            book_user.started_at = started_at
            book_user.finished_at = finished_at
        else:
            # Create new relationship
            book_user = BookUser(
                user_id=user_id,
                work_id=book.work_id,
                status=status,
                source=source,
                started_at=started_at,
                finished_at=finished_at
            )
            self.session.add(book_user)

        self.session.commit()
        return book_user 