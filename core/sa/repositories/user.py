from typing import List, Optional
from datetime import datetime, timedelta, UTC
from sqlalchemy import func, desc
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from core.sa.models import User, Book, BookUser, Library

class UserRepository:
    """Repository for managing User entities."""

    def __init__(self, session: Session):
        """Initialize the repository with a database session.
        
        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

    def create_user(self, name: str) -> User:
        """Create a new user.
        
        Args:
            name: The name of the user
            
        Returns:
            The created User object
            
        Raises:
            ValueError: If a user with the given name already exists
        """
        # Check if user already exists
        existing = self.session.query(User).filter(User.name == name).first()
        if existing:
            raise ValueError(f"User with name '{name}' already exists")

        user = User(name=name)
        self.session.add(user)
        try:
            self.session.commit()
            return user
        except IntegrityError:
            self.session.rollback()
            raise ValueError(f"User with name '{name}' already exists")

    def update_user(self, user_id: int, name: str) -> Optional[User]:
        """Update a user's details.
        
        Args:
            user_id: The ID of the user to update
            name: The new name for the user
            
        Returns:
            The updated User object if found, None otherwise
        """
        user = self.get_by_id(user_id)
        if not user:
            return None
            
        user.name = name
        self.session.commit()
        return user

    def delete_book_status(self, user_id: int, work_id: str) -> bool:
        """Delete a book status for a user.
        
        Args:
            user_id: The ID of the user
            work_id: The work ID of the book
            
        Returns:
            True if the status was deleted, False if not found
        """
        result = (
            self.session.query(BookUser)
            .filter(
                BookUser.user_id == user_id,
                BookUser.work_id == work_id
            )
            .delete()
        )
        self.session.commit()
        return result > 0

    def get_user_stats(self, user_id: int) -> dict:
        """Get reading statistics for a user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            Dictionary containing various reading statistics
        """
        user = self.get_user_with_books(user_id)
        if not user:
            return None

        # Get current year
        current_year = datetime.now(UTC).year
        
        # Calculate statistics
        total_books = len(user.book_users)
        books_read_this_year = sum(
            1 for bu in user.book_users 
            if bu.status == "completed" and bu.finished_at 
            and bu.finished_at.year == current_year
        )
        currently_reading = sum(1 for bu in user.book_users if bu.status == "reading")
        want_to_read = sum(1 for bu in user.book_users if bu.status == "want_to_read")
        
        # Calculate average rating if available
        completed_books = [bu.book for bu in user.book_users if bu.status == "completed"]
        ratings = [b.goodreads_rating for b in completed_books if b.goodreads_rating is not None]
        average_rating = sum(ratings) / len(ratings) if ratings else None
        
        # Calculate favorite genres
        genre_counts = {}
        for bu in user.book_users:
            for genre in bu.book.genres:
                genre_counts[genre.name] = genre_counts.get(genre.name, 0) + 1
        favorite_genres = sorted(genre_counts.keys(), key=lambda x: genre_counts[x], reverse=True)[:5]
        
        # Calculate reading pace (books per month)
        completed_statuses = [
            bu for bu in user.book_users 
            if bu.status == "completed" and bu.started_at and bu.finished_at
        ]
        if completed_statuses:
            total_reading_days = sum(
                (bu.finished_at - bu.started_at).days
                for bu in completed_statuses
            )
            reading_pace = (len(completed_statuses) * 30) / total_reading_days if total_reading_days > 0 else None
        else:
            reading_pace = None
        
        # Calculate total pages read
        total_pages = sum(
            bu.book.pages or 0
            for bu in user.book_users
            if bu.status == "completed" and bu.book.pages
        )
        
        return {
            "total_books": total_books,
            "books_read_this_year": books_read_this_year,
            "currently_reading": currently_reading,
            "want_to_read": want_to_read,
            "average_rating": average_rating,
            "favorite_genres": favorite_genres,
            "reading_pace": reading_pace,
            "total_pages_read": total_pages or None
        }

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
                .joinedload(Book.genres)
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
        # Get the book's work_id from the library table
        print(f"Looking for book with Goodreads ID: {goodreads_id}")
        library_entry = (
            self.session.query(Library)
            .filter(Library.goodreads_id == goodreads_id)
            .first()
        )
        if not library_entry:
            print(f"Library entry not found with Goodreads ID: {goodreads_id}")
            return None

        print(f"Found library entry: {library_entry.title} (work_id: {library_entry.work_id})")

        # Find existing book-user relationship or create new one
        book_user = (
            self.session.query(BookUser)
            .filter(
                BookUser.user_id == user_id,
                BookUser.work_id == library_entry.work_id
            )
            .first()
        )

        if book_user:
            print(f"Updating existing book status for user {user_id}")
            # Update existing relationship
            book_user.status = status
            book_user.source = source
            book_user.started_at = started_at
            book_user.finished_at = finished_at
        else:
            print(f"Creating new book status for user {user_id}")
            # Create new relationship
            book_user = BookUser(
                user_id=user_id,
                work_id=library_entry.work_id,
                status=status,
                source=source,
                started_at=started_at,
                finished_at=finished_at
            )
            self.session.add(book_user)

        try:
            self.session.commit()
            print("Successfully committed changes")
            return book_user
        except Exception as e:
            print(f"Error committing changes: {str(e)}")
            self.session.rollback()
            return None

    def get_or_create_user(self, name: str) -> User:
        """Get an existing user by name or create a new one.
        
        Args:
            name: The name of the user
            
        Returns:
            The existing or newly created User object
        """
        user = self.session.query(User).filter(User.name == name).first()
        if not user:
            user = User(name=name)
            self.session.add(user)
            self.session.commit()
        return user 