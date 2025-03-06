from typing import List, Optional
from datetime import datetime, timedelta, UTC
from sqlalchemy import func, desc, and_, or_, case, exists, distinct
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from core.sa.models import User, Book, BookUser, Library, BookAuthor, BookSeries, BookSimilar, Series, BookWanted, UserAuthorSubscription, UserSeriesSubscription, Author, Series, BookGenre, Genre

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
        return self.session.query(User).filter(User.id == user_id).one_or_none()

    def count_users(self) -> int:
        """Get the total number of users.
        
        Returns:
            Total number of users in the database
        """
        return self.session.query(User).count()

    def search_users(self, query: str, limit: int = 20, offset: int = 0) -> List[User]:
        """Search for users by name.
        
        Args:
            query: The search query string
            limit: Maximum number of results to return (default: 20)
            offset: Number of records to skip (default: 0)
            
        Returns:
            List of matching User objects
        """
        base_query = self.session.query(User)
        if query:
            base_query = base_query.filter(User.name.ilike(f"%{query}%"))
        return base_query.offset(offset).limit(limit).all()

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

    def get_user_books_by_statuses(
        self,
        user_id: int,
        statuses: List[str],
        limit: int = 20,
        offset: int = 0
    ) -> List[Book]:
        """Get books for a user with specific statuses.
        
        Args:
            user_id: The ID of the user
            statuses: List of book statuses to filter by (e.g., ['completed', 'reading'])
            limit: Maximum number of results to return
            offset: Number of records to skip
            
        Returns:
            List of Book objects with loaded relationships, ordered by finished_at date (NULL dates last)
        """
        return (
            self.session.query(Book)
            .join(BookUser, and_(
                BookUser.work_id == Book.work_id,
                BookUser.user_id == user_id,
                BookUser.status.in_(statuses)
            ))
            .options(
                joinedload(Book.book_authors).joinedload(BookAuthor.author),
                joinedload(Book.book_series).joinedload(BookSeries.series),
                joinedload(Book.book_users).joinedload(BookUser.book)
            )
            .order_by(
                case(
                    (BookUser.finished_at.is_(None), 1),
                    else_=0
                ),
                desc(BookUser.finished_at)
            )
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_user_books_by_statuses(
        self,
        user_id: int,
        statuses: List[str]
    ) -> int:
        """Count books for a user with specific statuses.
        
        Args:
            user_id: The ID of the user
            statuses: List of book statuses to filter by (e.g., ['completed', 'reading'])
            
        Returns:
            Total count of matching books
        """
        return (
            self.session.query(Book)
            .join(BookUser, and_(
                BookUser.work_id == Book.work_id,
                BookUser.user_id == user_id,
                BookUser.status.in_(statuses)
            ))
            .count()
        )

    def get_similar_books_for_user_reads(
        self,
        user_id: int,
        min_count: int = 1,
        limit: int = 20,
        offset: int = 0
    ) -> List[tuple[Book, int]]:
        """Get books that are marked as similar to the user's read books.
        
        Args:
            user_id: The ID of the user
            min_count: Minimum number of times a book should appear as similar
            limit: Maximum number of results to return
            offset: Number of records to skip
            
        Returns:
            List of tuples containing (Book, count) where count is the number of times
            the book appears as similar to the user's read books
        """
        # First get all the books the user has read
        read_books = (
            self.session.query(Book.work_id)
            .join(BookUser)
            .filter(
                BookUser.user_id == user_id,
                BookUser.status == "completed"
            )
        )
        
        # Then get similar books for those read books with their counts
        similar_books = (
            self.session.query(Book, func.count(Book.work_id).label('similar_count'))
            .join(BookSimilar, BookSimilar.similar_work_id == Book.work_id)
            .filter(BookSimilar.work_id.in_(read_books))
            .options(
                joinedload(Book.book_authors).joinedload(BookAuthor.author),
                joinedload(Book.book_series).joinedload(BookSeries.series)
            )
            .group_by(Book)
            .having(func.count(Book.work_id) >= min_count)
            .order_by(desc('similar_count'))
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        return similar_books

    def count_similar_books_for_user_reads(
        self,
        user_id: int,
        min_count: int = 1
    ) -> int:
        """Count books that are marked as similar to the user's read books.
        
        Args:
            user_id: The ID of the user
            min_count: Minimum number of times a book should appear as similar
            
        Returns:
            Total count of similar books meeting the minimum count criteria
        """
        # First get all the books the user has read
        read_books = (
            self.session.query(Book.work_id)
            .join(BookUser)
            .filter(
                BookUser.user_id == user_id,
                BookUser.status == "completed"
            )
        )
        
        # Then count similar books meeting the minimum count criteria
        return (
            self.session.query(func.count(func.distinct(Book.work_id)))
            .select_from(Book)
            .join(BookSimilar, BookSimilar.similar_work_id == Book.work_id)
            .filter(BookSimilar.work_id.in_(read_books))
            .group_by(Book.work_id)
            .having(func.count(Book.work_id) >= min_count)
            .count()
        )

    def get_user_read_genre_counts(self, user_id: int) -> List[tuple[str, int, List[Book]]]:
        """Get counts of genres from books the user has read, along with top unread books per genre.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            List of tuples containing (genre_name, count, top_unread_books) ordered by count descending
        """
        # Get all completed books for the user with their genres
        read_books = (
            self.session.query(Book)
            .join(BookUser)
            .filter(
                BookUser.user_id == user_id,
                BookUser.status == "completed"
            )
            .options(joinedload(Book.genres))
            .all()
        )
        print(f"Found {len(read_books)} read books for user {user_id}")
        
        # Get work_ids of all books the user has any status for (to exclude from unread)
        user_book_work_ids = set(
            book.work_id for book in
            self.session.query(Book)
            .join(BookUser)
            .filter(BookUser.user_id == user_id)
            .all()
        )
        print(f"User has {len(user_book_work_ids)} total books with any status")
        
        # Count genres and track books per genre
        genre_map = {}  # name -> count
        genre_books = {}  # name -> set of read book work_ids
        
        for book in read_books:
            for genre in book.genres:
                genre_map[genre.name] = genre_map.get(genre.name, 0) + 1
                if genre.name not in genre_books:
                    genre_books[genre.name] = set()
                genre_books[genre.name].add(book.work_id)
        
        print(f"Found {len(genre_map)} unique genres")
        
        # For each genre, get top 3 unread books by votes
        result = []
        for genre_name, count in sorted(genre_map.items(), key=lambda x: (-x[1], x[0])):
            print(f"\nProcessing genre: {genre_name} (count: {count})")
            
            # Get top 3 unread books for this genre
            top_unread = (
                self.session.query(Book)
                .join(Book.genres)
                .filter(
                    Book.genres.any(name=genre_name),
                    ~Book.work_id.in_(user_book_work_ids)
                )
                .options(
                    joinedload(Book.book_authors).joinedload(BookAuthor.author),
                    joinedload(Book.book_series).joinedload(BookSeries.series)
                )
                .order_by(
                    desc(Book.goodreads_votes),
                    desc(Book.goodreads_rating)
                )
                .distinct()  # Ensure we don't get duplicates
                .limit(10)  # Get top 10 books
                .all()
            )
            print(f"Found {len(top_unread)} unread books for genre {genre_name}")
            for book in top_unread:
                print(f"  - {book.title} (votes: {book.goodreads_votes})")
            
            result.append((genre_name, count, top_unread))
        
        return result

    def get_recommended_books(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0
    ) -> List[Book]:
        """Get recommended books based on similar books to what the user has read."""
        # Get all books the user has completed
        completed_books = (
            self.session.query(Book)
            .join(BookUser)
            .filter(
                BookUser.user_id == user_id,
                BookUser.status == "completed"
            )
            .all()
        )
        
        # Get all similar books for completed books
        similar_book_ids = []
        for book in completed_books:
            similar_books = (
                self.session.query(Book)
                .join(BookSimilar, Book.work_id == BookSimilar.similar_work_id)
                .filter(
                    BookSimilar.work_id == book.work_id,
                    Book.hidden.is_(False)  # Exclude hidden books
                )
                .all()
            )
            similar_book_ids.extend([book.work_id for book in similar_books])
        
        # Count occurrences of each similar book
        from collections import Counter
        book_counts = Counter(similar_book_ids)
        
        # Get the most frequent similar books, excluding books the user has already read
        recommended_books = (
            self.session.query(Book)
            .filter(
                Book.work_id.in_([bid for bid, _ in book_counts.most_common()]),
                Book.hidden.is_(False),  # Exclude hidden books
                ~exists().where(
                    and_(
                        BookUser.work_id == Book.work_id,
                        BookUser.user_id == user_id
                    )
                )
            )
            .order_by(
                # Order by frequency of appearance
                case(
                    {work_id: count for work_id, count in book_counts.most_common()},
                    value=Book.work_id
                ).desc()
            )
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        return recommended_books

    def count_recommended_books(self, user_id: int) -> int:
        """Count total number of recommended books for a user."""
        # Get all books the user has completed
        completed_books = (
            self.session.query(Book)
            .join(BookUser)
            .filter(
                BookUser.user_id == user_id,
                BookUser.status == "completed"
            )
            .all()
        )
        
        # Get all similar books for completed books
        similar_book_ids = []
        for book in completed_books:
            similar_books = (
                self.session.query(Book)
                .join(BookSimilar, Book.work_id == BookSimilar.similar_work_id)
                .filter(
                    BookSimilar.work_id == book.work_id,
                    Book.hidden.is_(False)  # Exclude hidden books
                )
                .all()
            )
            similar_book_ids.extend([book.work_id for book in similar_books])
        
        # Count unique similar books that user hasn't read
        return (
            self.session.query(func.count(distinct(Book.work_id)))
            .filter(
                Book.work_id.in_(set(similar_book_ids)),
                Book.hidden.is_(False),
                ~exists().where(
                    and_(
                        BookUser.work_id == Book.work_id,
                        BookUser.user_id == user_id
                    )
                )
            )
            .scalar() or 0
        )

    def get_on_deck_books(self, user_id: int, limit: int = 20, offset: int = 0) -> List[Book]:
        """
        Get books that are 'on deck' for the user to read next.
        This includes:
        1. Books currently being read
        2. Next unread books in series where the user has read previous books,
           ordered by when the user last read a book in each series
           (excluding series where a book is currently being read)
        
        Only includes published books (where source is not None and published_state is 'published').
        
        Args:
            user_id: The ID of the user
            limit: Maximum number of books to return
            offset: Number of books to skip
            
        Returns:
            List of Book objects ordered by priority (reading first, then next in series)
        """
        # First, get all books currently being read by the user
        reading_books = (
            self.session.query(Book)
            .join(BookUser)
            .filter(
                BookUser.user_id == user_id,
                BookUser.status == "reading",
                Book.source != None,  # Only include published books
                or_(
                    Book.published_state == "published",
                    Book.published_state == None
                ),
                Book.hidden.is_(False)
            )
            .options(
                joinedload(Book.book_authors).joinedload(BookAuthor.author),
                joinedload(Book.book_series).joinedload(BookSeries.series),
                joinedload(Book.book_users)
            )
            .all()
        )
        
        # Get series IDs where user is currently reading a book
        reading_series_ids = set()
        for book in reading_books:
            for book_series in book.book_series:
                reading_series_ids.add(book_series.series_id)
        
        # Get all series where the user has read at least one book, ordered by last read date
        # Exclude series where user is currently reading a book
        read_series = (
            self.session.query(Series, func.max(BookUser.finished_at).label('last_read'))
            .join(BookSeries)
            .join(Book)
            .join(BookUser)
            .filter(
                BookUser.user_id == user_id,
                BookUser.status == "completed",
                Book.source != None,  # Only include published books
                or_(
                    Book.published_state == "published",
                    Book.published_state == None
                ),
                ~Series.goodreads_id.in_(reading_series_ids)  # Exclude series being read
            )
            .group_by(Series)
            .order_by(desc('last_read'))
            .all()
        )
        
        # For each series, get the next unread book
        next_in_series_books = []
        for series, last_read in read_series:
            # Get the highest series_order of completed books in this series
            max_completed_order = (
                self.session.query(func.max(BookSeries.series_order))
                .join(Book)
                .join(BookUser)
                .filter(
                    BookSeries.series.has(goodreads_id=series.goodreads_id),
                    BookUser.user_id == user_id,
                    BookUser.status == "completed",
                    Book.source != None,
                    or_(
                        Book.published_state == "published",
                        Book.published_state == None
                    )
                )
                .scalar() or 0
            )
            
            # Get the next book in the series that hasn't been read
            next_book = (
                self.session.query(Book)
                .join(BookSeries)
                .outerjoin(BookUser, and_(
                    BookUser.work_id == Book.work_id,
                    BookUser.user_id == user_id
                ))
                .filter(
                    BookSeries.series.has(goodreads_id=series.goodreads_id),
                    BookSeries.series_order > max_completed_order,
                    Book.source != None,
                    or_(
                        Book.published_state == "published",
                        Book.published_state == None
                    ),
                    or_(
                        BookUser.work_id == None,  # No entry in book_users
                        and_(
                            BookUser.user_id == user_id,
                            BookUser.status.notin_(["completed", "reading"])
                        )
                    ),
                    Book.hidden.is_(False)
                )
                .options(
                    joinedload(Book.book_authors).joinedload(BookAuthor.author),
                    joinedload(Book.book_series).joinedload(BookSeries.series),
                    joinedload(Book.book_users)
                )
                .order_by(BookSeries.series_order)
                .first()
            )
            
            if next_book:
                next_in_series_books.append(next_book)
        
        # Combine and deduplicate the results
        all_books = reading_books + next_in_series_books
        unique_books = list(dict.fromkeys(all_books))  # Preserve order while deduplicating
        
        # Apply pagination
        paginated_books = unique_books[offset:offset + limit]
        
        # Process each book to include user status and wanted state
        processed_books = []
        for book in paginated_books:
            # Determine user's status for this book
            book_user = next(
                (bu for bu in book.book_users if bu.user_id == user_id), None
            )
            book.user_status = book_user.status if book_user else None

            # Check if the book is in the user's wanted list
            book.wanted = any(bw.user_id == user_id for bw in book.book_wanted)
            
            processed_books.append(book)
        
        return processed_books

    def add_wanted_book(self, user_id: int, work_id: str, source: str = "manual") -> Optional[BookWanted]:
        """Add a book to the user's wanted list.
        
        Args:
            user_id: The ID of the user
            work_id: The work ID of the book to add
            source: Where the book will be acquired from (default: "manual")
            
        Returns:
            The created BookWanted entry if successful, None if the book doesn't exist
            
        Raises:
            ValueError: If:
                1. The book is already in the user's wanted list (prevents duplicates)
                2. The book exists in the library (can't want what you already have)
        """
        # Validation 1: Check if the book exists in our books table
        # We can't want a book that we don't know about
        book = self.session.query(Book).filter(Book.work_id == work_id).first()
        if not book:
            return None
            
        # Validation 2: Check if already in wanted list
        # Prevents duplicate entries for the same book
        existing = (
            self.session.query(BookWanted)
            .filter(
                BookWanted.user_id == user_id,
                BookWanted.work_id == work_id
            )
            .first()
        )
        if existing:
            raise ValueError(f"Book {work_id} is already in user's wanted list")

        # Validation 3: Check if book exists in library
        # Can't want a book that's already in the library
        library_entry = (
            self.session.query(Library)
            .filter(Library.work_id == work_id)
            .first()
        )
        if library_entry:
            raise ValueError(f"Book {work_id} already exists in the library and cannot be marked as wanted")
            
        # All validations passed, create new wanted entry
        wanted = BookWanted(
            user_id=user_id,
            work_id=work_id,
            source=source
        )
        self.session.add(wanted)
        
        try:
            self.session.commit()
            return wanted
        except Exception as e:
            self.session.rollback()
            raise ValueError(f"Error adding book to wanted list: {str(e)}")

    def remove_wanted_book(self, user_id: int, work_id: str) -> bool:
        """Remove a book from the user's wanted list.
        
        Args:
            user_id: The ID of the user
            work_id: The work ID of the book to remove
            
        Returns:
            True if the book was removed, False if it wasn't in the wanted list
        """
        result = (
            self.session.query(BookWanted)
            .filter(
                BookWanted.user_id == user_id,
                BookWanted.work_id == work_id
            )
            .delete()
        )
        self.session.commit()
        return result > 0

    def get_wanted_books(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0
    ) -> List[tuple[BookWanted, Book]]:
        """Get a user's wanted books with full book information.
        
        Args:
            user_id: The ID of the user
            limit: Maximum number of results to return
            offset: Number of records to skip
            
        Returns:
            List of tuples containing (BookWanted, Book) pairs
        """
        return (
            self.session.query(BookWanted, Book)
            .join(Book, BookWanted.work_id == Book.work_id)
            .filter(BookWanted.user_id == user_id)
            .options(
                joinedload(Book.book_authors).joinedload(BookAuthor.author),
                joinedload(Book.book_series).joinedload(BookSeries.series)
            )
            .order_by(BookWanted.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    # Subscription Management Methods
    
    def subscribe_to_author(self, user_id: int, author_goodreads_id: str) -> Optional[UserAuthorSubscription]:
        """Subscribe a user to an author.
        
        Args:
            user_id: The ID of the user
            author_goodreads_id: The Goodreads ID of the author
            
        Returns:
            The created subscription if successful, None if the author doesn't exist
            
        Raises:
            ValueError: If the user is already subscribed to this author
        """
        # Check if author exists
        author = self.session.query(Author).filter(Author.goodreads_id == author_goodreads_id).first()
        if not author:
            return None
            
        # Check for existing subscription
        existing = (
            self.session.query(UserAuthorSubscription)
            .filter(
                UserAuthorSubscription.user_id == user_id,
                UserAuthorSubscription.author_goodreads_id == author_goodreads_id,
                UserAuthorSubscription.deleted_at.is_(None)  # Not soft deleted
            )
            .first()
        )
        if existing:
            raise ValueError(f"Already subscribed to author {author_goodreads_id}")
            
        # Create new subscription
        subscription = UserAuthorSubscription(
            user_id=user_id,
            author_goodreads_id=author_goodreads_id
        )
        self.session.add(subscription)
        
        try:
            self.session.commit()
            return subscription
        except Exception as e:
            self.session.rollback()
            raise ValueError(f"Error creating author subscription: {str(e)}")
            
    def subscribe_to_series(self, user_id: int, series_goodreads_id: str) -> Optional[UserSeriesSubscription]:
        """Subscribe a user to a series.
        
        Args:
            user_id: The ID of the user
            series_goodreads_id: The Goodreads ID of the series
            
        Returns:
            The created subscription if successful, None if the series doesn't exist
            
        Raises:
            ValueError: If the user is already subscribed to this series
        """
        # Check if series exists
        series = self.session.query(Series).filter(Series.goodreads_id == series_goodreads_id).first()
        if not series:
            return None
            
        # Check for existing subscription
        existing = (
            self.session.query(UserSeriesSubscription)
            .filter(
                UserSeriesSubscription.user_id == user_id,
                UserSeriesSubscription.series_goodreads_id == series_goodreads_id,
                UserSeriesSubscription.deleted_at.is_(None)  # Not soft deleted
            )
            .first()
        )
        if existing:
            raise ValueError(f"Already subscribed to series {series_goodreads_id}")
            
        # Create new subscription
        subscription = UserSeriesSubscription(
            user_id=user_id,
            series_goodreads_id=series_goodreads_id
        )
        self.session.add(subscription)
        
        try:
            self.session.commit()
            return subscription
        except Exception as e:
            self.session.rollback()
            raise ValueError(f"Error creating series subscription: {str(e)}")
            
    def unsubscribe_from_author(self, user_id: int, author_goodreads_id: str, hard_delete: bool = False) -> bool:
        """Unsubscribe a user from an author.
        
        Args:
            user_id: The ID of the user
            author_goodreads_id: The Goodreads ID of the author
            hard_delete: If True, removes the record; if False, soft deletes (default: False)
            
        Returns:
            True if unsubscribed successfully, False if subscription not found
        """
        subscription = (
            self.session.query(UserAuthorSubscription)
            .filter(
                UserAuthorSubscription.user_id == user_id,
                UserAuthorSubscription.author_goodreads_id == author_goodreads_id,
                UserAuthorSubscription.deleted_at.is_(None)  # Not already soft deleted
            )
            .first()
        )
        
        if not subscription:
            return False
            
        if hard_delete:
            self.session.delete(subscription)
        else:
            subscription.deleted_at = datetime.now(UTC)
            
        self.session.commit()
        return True
        
    def unsubscribe_from_series(self, user_id: int, series_goodreads_id: str, hard_delete: bool = False) -> bool:
        """Unsubscribe a user from a series.
        
        Args:
            user_id: The ID of the user
            series_goodreads_id: The Goodreads ID of the series
            hard_delete: If True, removes the record; if False, soft deletes (default: False)
            
        Returns:
            True if unsubscribed successfully, False if subscription not found
        """
        subscription = (
            self.session.query(UserSeriesSubscription)
            .filter(
                UserSeriesSubscription.user_id == user_id,
                UserSeriesSubscription.series_goodreads_id == series_goodreads_id,
                UserSeriesSubscription.deleted_at.is_(None)  # Not already soft deleted
            )
            .first()
        )
        
        if not subscription:
            return False
            
        if hard_delete:
            self.session.delete(subscription)
        else:
            subscription.deleted_at = datetime.now(UTC)
            
        self.session.commit()
        return True
        
    def restore_author_subscription(self, user_id: int, author_goodreads_id: str) -> bool:
        """Restore a soft-deleted author subscription.
        
        Args:
            user_id: The ID of the user
            author_goodreads_id: The Goodreads ID of the author
            
        Returns:
            True if restored successfully, False if subscription not found or not soft-deleted
        """
        subscription = (
            self.session.query(UserAuthorSubscription)
            .filter(
                UserAuthorSubscription.user_id == user_id,
                UserAuthorSubscription.author_goodreads_id == author_goodreads_id,
                UserAuthorSubscription.deleted_at.isnot(None)  # Must be soft deleted
            )
            .first()
        )
        
        if not subscription:
            return False
            
        subscription.deleted_at = None
        self.session.commit()
        return True
        
    def restore_series_subscription(self, user_id: int, series_goodreads_id: str) -> bool:
        """Restore a soft-deleted series subscription.
        
        Args:
            user_id: The ID of the user
            series_goodreads_id: The Goodreads ID of the series
            
        Returns:
            True if restored successfully, False if subscription not found or not soft-deleted
        """
        subscription = (
            self.session.query(UserSeriesSubscription)
            .filter(
                UserSeriesSubscription.user_id == user_id,
                UserSeriesSubscription.series_goodreads_id == series_goodreads_id,
                UserSeriesSubscription.deleted_at.isnot(None)  # Must be soft deleted
            )
            .first()
        )
        
        if not subscription:
            return False
            
        subscription.deleted_at = None
        self.session.commit()
        return True
        
    def get_author_subscriptions(
        self,
        user_id: int,
        include_deleted: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[tuple[UserAuthorSubscription, Author]]:
        """Get a user's author subscriptions with full author information.
        
        Args:
            user_id: The ID of the user
            include_deleted: Whether to include soft-deleted subscriptions (default: False)
            limit: Maximum number of results to return
            offset: Number of records to skip
            
        Returns:
            List of tuples containing (UserAuthorSubscription, Author) pairs
        """
        query = (
            self.session.query(UserAuthorSubscription, Author)
            .join(Author, UserAuthorSubscription.author_goodreads_id == Author.goodreads_id)
            .filter(UserAuthorSubscription.user_id == user_id)
        )
        
        if not include_deleted:
            query = query.filter(UserAuthorSubscription.deleted_at.is_(None))
            
        query = query.order_by(UserAuthorSubscription.created_at.desc())
        
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
            
        return query.all()
        
    def get_series_subscriptions(
        self,
        user_id: int,
        include_deleted: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[tuple[UserSeriesSubscription, Series]]:
        """Get a user's series subscriptions with full series information.
        
        Args:
            user_id: The ID of the user
            include_deleted: Whether to include soft-deleted subscriptions (default: False)
            limit: Maximum number of results to return
            offset: Number of records to skip
            
        Returns:
            List of tuples containing (UserSeriesSubscription, Series) pairs
        """
        query = (
            self.session.query(UserSeriesSubscription, Series)
            .join(Series, UserSeriesSubscription.series_goodreads_id == Series.goodreads_id)
            .filter(UserSeriesSubscription.user_id == user_id)
        )
        
        if not include_deleted:
            query = query.filter(UserSeriesSubscription.deleted_at.is_(None))
            
        query = query.order_by(UserSeriesSubscription.created_at.desc())
        
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
            
        return query.all()
        
    def is_subscribed_to_author(self, user_id: int, author_goodreads_id: str, include_deleted: bool = False) -> bool:
        """Check if a user is subscribed to an author.
        
        Args:
            user_id: The ID of the user
            author_goodreads_id: The Goodreads ID of the author
            include_deleted: Whether to include soft-deleted subscriptions (default: False)
            
        Returns:
            True if subscribed, False otherwise
        """
        query = (
            self.session.query(UserAuthorSubscription)
            .filter(
                UserAuthorSubscription.user_id == user_id,
                UserAuthorSubscription.author_goodreads_id == author_goodreads_id
            )
        )
        
        if not include_deleted:
            query = query.filter(UserAuthorSubscription.deleted_at.is_(None))
            
        return query.first() is not None
        
    def is_subscribed_to_series(self, user_id: int, series_goodreads_id: str, include_deleted: bool = False) -> bool:
        """Check if a user is subscribed to a series.
        
        Args:
            user_id: The ID of the user
            series_goodreads_id: The Goodreads ID of the series
            include_deleted: Whether to include soft-deleted subscriptions (default: False)
            
        Returns:
            True if subscribed, False otherwise
        """
        query = (
            self.session.query(UserSeriesSubscription)
            .filter(
                UserSeriesSubscription.user_id == user_id,
                UserSeriesSubscription.series_goodreads_id == series_goodreads_id
            )
        )
        
        if not include_deleted:
            query = query.filter(UserSeriesSubscription.deleted_at.is_(None))
            
        return query.first() is not None

    def get_series_books_with_user_status(
        self,
        user_id: int,
        series_goodreads_id: str
    ) -> List[Book]:
        """Get all books in a series with their read status for a user.
        
        Args:
            user_id: The ID of the user
            series_goodreads_id: The Goodreads ID of the series
            
        Returns:
            List of Book objects with loaded relationships, ordered by series position
        """
        return (
            self.session.query(Book)
            .join(BookSeries)
            .filter(
                BookSeries.series_id == series_goodreads_id,
                Book.hidden.is_(False)
            )
            .options(
                joinedload(Book.book_authors).joinedload(BookAuthor.author),
                joinedload(Book.book_series).joinedload(BookSeries.series),
                joinedload(Book.book_users)
            )
            .order_by(BookSeries.series_order)
            .all()
        )

    def get_series_books(self, series_id: str) -> List[Book]:
        """Get the first three books in a series by release date.
        
        Args:
            series_id: The Goodreads ID of the series
            
        Returns:
            List of up to three Book objects, ordered by published_date
        """
        return (
            self.session.query(Book)
            .join(BookSeries)
            .filter(BookSeries.series.has(goodreads_id=series_id))
            .order_by(Book.published_date)
            .all()
        )

    def get_series_author_id(self, series_id: str) -> Optional[str]:
        """Get the Goodreads ID of the author of the first book in a series.
        
        Args:
            series_id: The Goodreads ID of the series
            
        Returns:
            The author's Goodreads ID if found, None otherwise
        """
        first_book = (
            self.session.query(Book)
            .join(BookSeries)
            .join(BookAuthor)
            .filter(
                BookSeries.series.has(goodreads_id=series_id),
                BookAuthor.role == "Author"
            )
            .order_by(Book.published_date)
            .first()
        )
        
        if first_book and first_book.book_authors:
            for ba in first_book.book_authors:
                if ba.role == "Author":
                    return ba.author.goodreads_id
        return None

    def get_recent_books(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0
    ) -> List[Book]:
        """Get recently created books.
        
        Args:
            user_id: The ID of the user (for loading user-specific status)
            limit: Maximum number of results to return
            offset: Number of records to skip
            
        Returns:
            List of Book objects ordered by created_at date
        """
        return (
            self.session.query(Book)
            .options(
                joinedload(Book.book_authors).joinedload(BookAuthor.author),
                joinedload(Book.book_series).joinedload(BookSeries.series),
                joinedload(Book.book_users)
            )
            .filter(
                Book.hidden == False,
                Book.source != None
            )
            .order_by(desc(Book.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_recent_books(self) -> int:
        """Get total count of books for pagination.
        
        Returns:
            Total number of non-hidden books
        """
        return (
            self.session.query(Book)
            .filter(
                Book.hidden == False,
                Book.source != None
            )
            .count()
        )

    def get_book_status(self, user_id: int, goodreads_id: str) -> Optional[BookUser]:
        """Get the existing book status for a user.
        
        Args:
            user_id: The user's ID
            goodreads_id: The book's Goodreads ID
            
        Returns:
            The BookUser record if it exists, None otherwise
        """
        return (self.session.query(BookUser)
                .join(Book, Book.work_id == BookUser.work_id)
                .filter(
                    BookUser.user_id == user_id,
                    Book.goodreads_id == goodreads_id
                )
                .first()) 