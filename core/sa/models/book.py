# core/sa/models/book.py
from datetime import datetime, UTC
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, ForeignKey, Table, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .base import Base, TimestampMixin, LastSyncedMixin
from enum import Enum

class HiddenReason(str, Enum):
    # Vote/Data Quality
    LOW_VOTE_COUNT = "low_vote_count"           # Too few votes to be reliable
    NO_DESCRIPTION = "no_description"           # Missing book description
    EXCEEDS_PAGE_LENGTH = "exceeds_page_length" # Page count too high
    PAGE_COUNT_UNKNOWN = "page_count_unknown"   # Missing page count

    # Language
    NO_ENGLISH_EDITIONS = "no_english_editions" # No English editions found

    # Excluded Format/Genre
    EXCLUDED_GENRE = "excluded_genre"           # Book in an excluded genre (manga, etc)
    INVALID_FORMAT = "invalid_format"           # Invalid book format

    # Title Issues
    TITLE_PATTERN_MATCH = "title_pattern_match"     # Title contains excluded pattern
    TITLE_NUMBER_PATTERN = "title_number_pattern"   # Title contains number pattern
    COMBINED_EDITION = "combined_edition"           # Book is a combined edition of multiple books

    # Publication Info
    INVALID_PUBLICATION = "invalid_publication" # Invalid or missing publication info
    
    # Manually hidden by user
    MANUAL = "manual"        # Manually hidden by user

class BookAuthor(Base, TimestampMixin):
    __tablename__ = 'book_author'

    work_id: Mapped[str] = mapped_column(String(255), ForeignKey('book.work_id'), primary_key=True)
    author_id: Mapped[str] = mapped_column(String(255), ForeignKey('author.goodreads_id'), primary_key=True)
    role: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    book = relationship('Book', back_populates='book_authors')
    author = relationship('Author', back_populates='book_authors')

    __table_args__ = (
        Index('idx_book_author_work_id', 'work_id'),
        Index('idx_book_author_author_id', 'author_id'),
        {'schema': 'public'}
    )

class BookGenre(Base, TimestampMixin):
    __tablename__ = 'book_genre'

    work_id: Mapped[str] = mapped_column(String(255), ForeignKey('book.work_id'), primary_key=True)
    genre_id: Mapped[int] = mapped_column(ForeignKey('genre.id'), primary_key=True)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    book = relationship('Book', back_populates='book_genres')
    genre = relationship('Genre', back_populates='book_genres')

    __table_args__ = (
        Index('idx_book_genre_work_id', 'work_id'),
        Index('idx_book_genre_genre_id', 'genre_id'),
        {'schema': 'public'}
    )

class BookSimilar(Base, TimestampMixin):
    __tablename__ = 'book_similar'

    work_id: Mapped[str] = mapped_column(String(255), ForeignKey('book.work_id'), primary_key=True)
    similar_work_id: Mapped[str] = mapped_column(String(255), ForeignKey('book.work_id'), primary_key=True)

    # Relationships
    book = relationship('Book', foreign_keys=[work_id], back_populates='similar_to')
    similar_book = relationship('Book', foreign_keys=[similar_work_id], back_populates='similar_books')

    __table_args__ = (
        Index('idx_book_similar_work_id', 'work_id'),
        Index('idx_book_similar_similar_work_id', 'similar_work_id'),
        {'schema': 'public'}
    )

class BookScraped(Base, TimestampMixin):
    """Reference table for tracking which Goodreads IDs have been scraped and their work IDs"""
    __tablename__ = 'book_scraped'

    goodreads_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    work_id: Mapped[str | None] = mapped_column(String(255), ForeignKey('book.work_id'), nullable=True)
    book = relationship('Book', back_populates='book_scraped', foreign_keys=[work_id])

    __table_args__ = (
        Index('idx_book_scraped_work_id', 'work_id'),
        {'schema': 'public'}
    )

class Book(Base, TimestampMixin, LastSyncedMixin):
    __tablename__ = 'book'

    goodreads_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    work_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    published_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_state: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    goodreads_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    goodreads_votes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    hidden_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
    similar_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scraping_priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_scrape_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    book_authors = relationship('BookAuthor', back_populates='book')
    book_genres = relationship('BookGenre', back_populates='book')
    book_users = relationship('BookUser', back_populates='book')
    book_wanted = relationship('BookWanted', back_populates='book')
    book_series = relationship('BookSeries', back_populates='book')
    library_entries = relationship('Library', back_populates='book')
    similar_to = relationship('BookSimilar', foreign_keys=[BookSimilar.work_id], back_populates='book')
    similar_books = relationship('BookSimilar', foreign_keys=[BookSimilar.similar_work_id], back_populates='similar_book')
    book_scraped = relationship('BookScraped', back_populates='book')

    # Convenience relationships
    authors = relationship('Author', secondary='book_author', viewonly=True)
    genres = relationship('Genre', secondary='book_genre', viewonly=True)
    users = relationship('User', secondary='book_user', viewonly=True)
    series = relationship('Series', secondary='book_series', viewonly=True)

    __table_args__ = (
        # Main search and filter indexes
        Index('idx_book_title', 'title'),
        Index('idx_book_work_id', 'work_id'),
        Index('idx_book_published_date', 'published_date'),
        Index('idx_book_goodreads_votes', 'goodreads_votes'),
        Index('idx_book_goodreads_rating', 'goodreads_rating'),
        
        # Status and priority indexes
        Index('idx_book_hidden', 'hidden'),
        Index('idx_book_scraping_priority', 'scraping_priority'),
        Index('idx_book_next_scrape_at', 'next_scrape_at'),
        
        # Composite indexes for common queries
        Index('idx_book_rating_votes', 'goodreads_rating', 'goodreads_votes'),
        Index('idx_book_hidden_priority', 'hidden', 'scraping_priority'),
        
        {'schema': 'public'}
    )