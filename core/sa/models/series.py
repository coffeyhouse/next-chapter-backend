# core/sa/models/series.py
from sqlalchemy import Column, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class BookSeries(Base, TimestampMixin):
    """Association model for books in series"""
    __tablename__ = 'book_series'

    work_id = Column(String, ForeignKey('book.work_id'), primary_key=True)
    series_id = Column(String, ForeignKey('series.goodreads_id'), primary_key=True)
    series_order = Column(Float)

class Series(Base, TimestampMixin):
    __tablename__ = 'series'

    goodreads_id = Column(String, primary_key=True)
    title = Column(String, nullable=False)

    # Relationships
    books = relationship('Book', secondary='book_series', back_populates='series')