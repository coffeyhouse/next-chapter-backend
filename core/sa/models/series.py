# core/sa/models/series.py
from sqlalchemy import String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .base import Base, TimestampMixin, LastSyncedMixin
from datetime import datetime, UTC

class BookSeries(Base, TimestampMixin):
    """Association model for books in series"""
    __tablename__ = 'book_series'

    work_id: Mapped[str] = mapped_column(String(255), ForeignKey('book.work_id'), primary_key=True)
    series_id: Mapped[str] = mapped_column(String(255), ForeignKey('series.goodreads_id'), primary_key=True)
    series_order: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Usually short like "1", "1.5", "Book 1" etc.

    # Relationships
    book = relationship('Book', back_populates='book_series')
    series = relationship('Series', back_populates='book_series')

class Series(Base, TimestampMixin, LastSyncedMixin):
    __tablename__ = 'series'

    goodreads_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)  # Match book title length
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relationships
    book_series = relationship('BookSeries', back_populates='series')
    
    # Convenience relationship
    books = relationship('Book', secondary='book_series', viewonly=True)
    user_subscriptions = relationship('UserSeriesSubscription', back_populates='series')