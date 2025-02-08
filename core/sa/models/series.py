# core/sa/models/series.py
from sqlalchemy import Column, String, Float, ForeignKey, Table
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

# Association table for books in series
book_series = Table(
    'book_series',
    Base.metadata,
    Column('work_id', String, ForeignKey('book.work_id'), primary_key=True),
    Column('series_id', String, ForeignKey('series.goodreads_id'), primary_key=True),
    Column('series_order', Float)
)

class Series(Base, TimestampMixin):
    __tablename__ = 'series'

    goodreads_id = Column(String, primary_key=True)
    title = Column(String, nullable=False)

    # Relationships
    books = relationship('Book', secondary=book_series, back_populates='series')