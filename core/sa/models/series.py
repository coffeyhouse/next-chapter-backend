# core/sa/models/series.py
from sqlalchemy import String, Float, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .base import Base, TimestampMixin, LastSyncedMixin

class BookSeries(Base, TimestampMixin):
    """Association model for books in series"""
    __tablename__ = 'book_series'

    work_id: Mapped[str] = mapped_column(ForeignKey('book.work_id'), primary_key=True)
    series_id: Mapped[str] = mapped_column(ForeignKey('series.goodreads_id'), primary_key=True)
    series_order: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    book = relationship('Book', back_populates='book_series')
    series = relationship('Series', back_populates='book_series')

class Series(Base, TimestampMixin, LastSyncedMixin):
    __tablename__ = 'series'

    goodreads_id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)

    # Relationships
    book_series = relationship('BookSeries', back_populates='series')
    
    # Convenience relationship
    books = relationship('Book', secondary='book_series', viewonly=True)