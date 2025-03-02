# core/sa/repositories/book.py
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import select, desc, not_, exists, func, case, and_, or_
from sqlalchemy.orm import Session, joinedload
from ..models import Book, Author, Genre, Series, BookSimilar, BookAuthor, BookSeries, BookUser

class BookRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_goodreads_id(self, goodreads_id: str) -> Optional[Book]:
        """Get a book by its Goodreads ID"""
        return self.session.query(Book).filter(Book.goodreads_id == goodreads_id).first()

    def get_by_work_id(self, work_id: str) -> Optional[Book]:
        """Get a book by its work ID with all relationships loaded.
        
        Args:
            work_id: The work ID of the book
            
        Returns:
            Book object with loaded relationships (authors, series, genres, similar books, user status)
            or None if not found
        """
        return (
            self.session.query(Book)
            .filter(Book.work_id == work_id)
            .options(
                joinedload(Book.book_authors).joinedload(BookAuthor.author),
                joinedload(Book.book_series).joinedload(BookSeries.series),
                joinedload(Book.genres),
                joinedload(Book.book_users),
                joinedload(Book.similar_to).joinedload(BookSimilar.similar_book),
                joinedload(Book.similar_books).joinedload(BookSimilar.book)
            )
            .first()
        )

    def search_books(
        self, 
        query: Optional[str] = None,
        source: Optional[str] = None,
        sort_field: str = "goodreads_votes",
        sort_order: str = "desc",
        limit: int = 20,
        offset: int = 0
    ) -> List[Book]:
        """Search books by title and include author relationships.
        
        Args:
            query: Search query string
            source: Filter by source
            sort_field: Field to sort by (goodreads_votes, goodreads_rating, title, published_date, created_at)
            sort_order: Sort order (asc or desc)
            limit: Maximum number of results to return
            offset: Number of records to skip
            
        Returns:
            List of Book objects with loaded author relationships
        """
        base_query = self.session.query(Book).options(
            joinedload(Book.book_authors).joinedload(BookAuthor.author),
            joinedload(Book.genres),
            joinedload(Book.series)
        )
        
        if query and query.strip():
            base_query = base_query.filter(Book.title.ilike(f"%{query}%"))
            
        if source:
            base_query = base_query.filter(Book.source == source)
        
        # Apply sorting
        valid_sort_fields = {
            "goodreads_votes": Book.goodreads_votes,
            "goodreads_rating": Book.goodreads_rating,
            "title": Book.title,
            "published_date": Book.published_date,
            "created_at": Book.created_at
        }
        
        sort_column = valid_sort_fields.get(sort_field, Book.goodreads_votes)
        if sort_order == "desc":
            base_query = base_query.order_by(desc(sort_column))
        else:
            base_query = base_query.order_by(sort_column)
        
        return base_query.offset(offset).limit(limit).all()
        
    def count_books(
        self,
        query: Optional[str] = None,
        source: Optional[str] = None
    ) -> int:
        """Count total books matching the search criteria.
        
        Args:
            query: Search query string
            source: Filter by source
            
        Returns:
            Total count of matching books
        """
        base_query = self.session.query(Book)
        
        if query and query.strip():
            base_query = base_query.filter(Book.title.ilike(f"%{query}%"))
            
        if source:
            base_query = base_query.filter(Book.source == source)
            
        return base_query.count()

    def get_books_by_author(
        self,
        author_id: str,
        user_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Book]:
        """Get books by an author, sorted by publication date (newest first).
        
        Args:
            author_id: The Goodreads ID of the author
            user_id: Optional user ID to include read status and wanted status
            limit: Maximum number of books to return
            offset: Number of books to skip
            
        Returns:
            List of Book objects with loaded relationships, sorted by publication date descending,
            excluding hidden books
        """
        query = (
            self.session.query(Book)
            .join(BookAuthor)
            .filter(
                BookAuthor.author_id == author_id,
                Book.hidden.is_(False)  # Exclude hidden books
            )
            .options(
                joinedload(Book.book_authors).joinedload(BookAuthor.author),
                joinedload(Book.book_series).joinedload(BookSeries.series)
            )
        )
        
        # Add user-specific relationships if user_id provided
        if user_id is not None:
            query = query.options(
                joinedload(Book.book_users),
                joinedload(Book.book_wanted)
            )
            
        # Sort by publication date (newest first, nulls last)
        query = query.order_by(
            Book.published_date.desc().nulls_last(),
            Book.title.asc()
        )
        
        return query.offset(offset).limit(limit).all()

    def count_books_by_author(self, author_id: str) -> int:
        """Count total books by an author.
        
        Args:
            author_id: The Goodreads ID of the author
            
        Returns:
            Total count of non-hidden books by the author
        """
        return (
            self.session.query(func.count(Book.work_id))
            .join(BookAuthor)
            .filter(
                BookAuthor.author_id == author_id,
                Book.hidden.is_(False)  # Exclude hidden books from count
            )
            .scalar() or 0
        )

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

    def get_books_without_similar(self, source: Optional[str] = None) -> List[Book]:
        """Get books that don't have any similar books synced yet.
        
        Args:
            source: Optional source filter:
                   - 'library' for library books
                   - 'read' for books that any user has read
                   - any other source value will filter by that source
            
        Returns:
            List of Book objects that haven't been synced for similar books
        """
        # Start with base query
        query = self.session.query(Book)
        
        # Add source filter if specified
        if source:
            if source == 'read':
                # Find books that any user has read
                query = (
                    query
                    .join(BookUser)
                    .filter(BookUser.status == 'completed')
                    .distinct()
                )
            else:
                query = query.filter(Book.source == source)
        
        # Filter for books that haven't been synced for similar books
        # and are not hidden
        query = query.filter(
            Book.similar_synced_at.is_(None),
            Book.hidden.is_(False)  # Add filter for non-hidden books
        )
        
        # Only include published books with ratings and votes
        query = query.filter(
            Book.source.isnot(None),  # Source must not be None
            or_(
                Book.published_state == "published",
                Book.published_state.is_(None)  # Allow None published_state
            ),
            Book.published_date >= '2000-01-01',  # Only books published after 2000
            Book.published_date.isnot(None),  # Ensure we have a publication date
            Book.goodreads_rating.isnot(None),  # Must have a rating
            Book.goodreads_votes.isnot(None)  # Must have votes
        )
        
        # Order by rating and votes desc so we process popular books first
        books = query.order_by(
            Book.goodreads_votes.desc().nulls_last(),
            Book.goodreads_rating.desc().nulls_last()
        ).all()

        # Debug log the order
        print("\nBooks to process for similar books:")
        for book in books[:10]:  # Show first 10 for debugging
            print(f"- {book.title}: rating={book.goodreads_rating}, votes={book.goodreads_votes}, published={book.published_date}")
            
        return books

    def get_series_with_counts(
        self,
        query: Optional[str] = None,
        user_id: Optional[int] = None,
        sort_by: str = "book_count",
        limit: int = 20,
        offset: int = 0
    ) -> List[tuple[Series, int, int]]:
        """Get series with their book counts and user read counts.
        
        Args:
            query: Optional search string to filter series by title
            user_id: Optional user ID to get read counts for
            sort_by: Sort by 'book_count' or 'read_count'
            limit: Maximum number of results to return
            offset: Number of records to skip
            
        Returns:
            List of tuples containing (Series, total_book_count, user_read_count)
        """
        # Subquery to count completed books for the user in each series
        if user_id is not None:
            user_read_count = (
                func.count(
                    func.distinct(
                        case(
                            (and_(
                                BookUser.user_id == user_id,
                                BookUser.status == "completed"
                            ), Book.work_id),
                            else_=None
                        )
                    )
                ).label('user_read_count')
            )
        else:
            # For SQLite, use a simpler expression that always returns 0
            user_read_count = func.count(None).label('user_read_count')
            user_read_count = (user_read_count - user_read_count).label('user_read_count')

        base_query = (
            self.session.query(
                Series,
                func.count(func.distinct(Book.work_id)).label('book_count'),
                user_read_count
            )
            .select_from(Series)
            .join(BookSeries, Series.goodreads_id == BookSeries.series_id)
            .join(Book, Book.work_id == BookSeries.work_id)
        )
        
        if user_id is not None:
            base_query = base_query.outerjoin(
                BookUser,
                and_(
                    BookUser.work_id == Book.work_id,
                    BookUser.user_id == user_id,
                    BookUser.status == "completed"
                )
            )
        
        base_query = base_query.group_by(Series)
        
        if query and query.strip():
            base_query = base_query.filter(Series.title.ilike(f"%{query}%"))
            
        # Apply sorting
        if sort_by == "read_count":
            base_query = base_query.order_by(desc('user_read_count'), desc('book_count'), Series.title)
        else:  # Default to book_count
            base_query = base_query.order_by(desc('book_count'), Series.title)
            
        return base_query.offset(offset).limit(limit).all()
        
    def count_series(self, query: Optional[str] = None) -> int:
        """Count total number of series.
        
        Args:
            query: Optional search string to filter series by title
            
        Returns:
            Total count of series matching the criteria
        """
        base_query = self.session.query(Series)
        
        if query and query.strip():
            base_query = base_query.filter(Series.title.ilike(f"%{query}%"))
            
        return base_query.count()

    def get_all_books_with_images(self, force: bool = False) -> List[Book]:
        """Get books that need image conversion.
        
        Args:
            force: If True, get all books with images regardless of format.
                  If False, only get books with non-WebP images.
        
        Returns:
            List of Book objects that need image processing
        """
        query = self.session.query(Book).filter(Book.image_url.isnot(None))
        
        if not force:
            # Only get books that don't already have WebP images
            query = query.filter(not_(Book.image_url.like('%.webp')))
            
        return query.all()

    def update_book_status(
        self,
        user_id: int,
        work_id: str,
        status: Optional[str],
        source: Optional[str] = None,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
        update_none: bool = False
    ) -> Optional[BookUser]:
        """Update or create a book status for a user.
        
        Args:
            user_id: ID of the user
            work_id: Work ID of the book
            status: Reading status (reading, completed)
            source: Optional source of the book
            started_at: Optional start date
            finished_at: Optional finish date
            update_none: If True, None values will be applied (used to explicitly set nulls)
            
        Returns:
            Updated or created BookUser object, or None if book not found
        """
        # Get the book first
        book = self.get_by_work_id(work_id)
        if not book:
            return None
            
        # Check if status already exists
        book_user = (
            self.session.query(BookUser)
            .filter(
                BookUser.user_id == user_id,
                BookUser.work_id == work_id
            )
            .first()
        )
        
        if book_user:
            # Update existing status
            if status is not None or update_none:
                book_user.status = status
            if source is not None or update_none:
                book_user.source = source
            if started_at is not None or update_none:
                book_user.started_at = started_at
            if finished_at is not None or update_none:
                book_user.finished_at = finished_at
        else:
            # Create new status
            book_user = BookUser(
                user_id=user_id,
                work_id=work_id,
                status=status,
                source=source,
                started_at=started_at,
                finished_at=finished_at
            )
            self.session.add(book_user)
            
        try:
            self.session.commit()
            return book_user
        except:
            self.session.rollback()
            raise

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