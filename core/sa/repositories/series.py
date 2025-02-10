# core/sa/repositories/series.py

from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from core.sa.models import Series, Book, BookSeries
from datetime import datetime, timedelta, UTC
from sqlalchemy import or_

class SeriesRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_goodreads_id(self, goodreads_id: str) -> Optional[Series]:
        """
        Fetch a series by its Goodreads ID.
        """
        return self.session.query(Series).filter(Series.goodreads_id == goodreads_id).first()

    def search_series(self, query: str, limit: int = 20) -> List[Series]:
        """
        Search for series whose titles match the given query (case-insensitive).
        """
        return (
            self.session.query(Series)
            .filter(Series.title.ilike(f"%{query}%"))
            .limit(limit)
            .all()
        )

    def get_series_with_books(self, goodreads_id: str) -> Optional[Series]:
        """
        Retrieve a series by its Goodreads ID along with its associated books.
        This uses joined loading to minimize additional database queries.
        """
        return (
            self.session.query(Series)
            .options(
                joinedload(Series.book_series).joinedload(BookSeries.book)
            )
            .filter(Series.goodreads_id == goodreads_id)
            .first()
        )

    def get_series_by_book(self, book_id: str) -> List[Series]:
        """
        Get all series that include a specific book.
        """
        return (
            self.session.query(Series)
            .join(Series.book_series)
            .join(BookSeries.book)
            .filter(Book.goodreads_id == book_id)
            .all()
        )

    def get_recent_series(self, limit: int = 10) -> List[Series]:
        """
        Get the most recently added series, ordered by the created_at timestamp.
        """
        return (
            self.session.query(Series)
            .order_by(Series.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_series_needing_sync(self, days: int, limit: Optional[int] = None, source: Optional[str] = None) -> List[Series]:
        """
        Get series that haven't been synced in the specified number of days.
        Optionally filter by source of the books in the series.
        
        Args:
            days: Number of days since last sync
            limit: Maximum number of series to return
            source: Only include series with books from this source
            
        Returns:
            List of Series objects that need updating
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=days)
        query = self.session.query(Series).filter(
            or_(
                Series.last_synced_at.is_(None),
                Series.last_synced_at < cutoff_date
            )
        )
        
        # If source is specified, only include series that have books from that source
        if source:
            query = query.join(Series.book_series).join(BookSeries.book).filter(Book.source == source)
            
        # Order by last sync date, nulls first
        query = query.order_by(Series.last_synced_at.asc().nullsfirst())
            
        if limit:
            query = query.limit(limit)
            
        return query.all()
