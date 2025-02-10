# core/sa/models/book.py
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, Table, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .base import Base, TimestampMixin, LastSyncedMixin

class BookAuthor(Base, TimestampMixin):
    __tablename__ = 'book_author'

    work_id: Mapped[str] = mapped_column(ForeignKey('book.work_id'), primary_key=True)
    author_id: Mapped[str] = mapped_column(ForeignKey('author.goodreads_id'), primary_key=True)
    role: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    book = relationship('Book', back_populates='book_authors')
    author = relationship('Author', back_populates='book_authors')

class BookGenre(Base, TimestampMixin):
    __tablename__ = 'book_genre'

    work_id: Mapped[str] = mapped_column(ForeignKey('book.work_id'), primary_key=True)
    genre_id: Mapped[int] = mapped_column(ForeignKey('genre.id'), primary_key=True)

    # Relationships
    book = relationship('Book', back_populates='book_genres')
    genre = relationship('Genre', back_populates='book_genres')

class BookSimilar(Base, TimestampMixin):
    __tablename__ = 'book_similar'

    work_id: Mapped[str] = mapped_column(ForeignKey('book.work_id'), primary_key=True)
    similar_work_id: Mapped[str] = mapped_column(ForeignKey('book.work_id'), primary_key=True)

    # Relationships
    book = relationship('Book', foreign_keys=[work_id], back_populates='similar_to')
    similar_book = relationship('Book', foreign_keys=[similar_work_id], back_populates='similar_books')

class BookScraped(Base, TimestampMixin):
    """Reference table for tracking which Goodreads IDs have been scraped and their work IDs"""
    __tablename__ = 'book_scraped'

    goodreads_id: Mapped[str] = mapped_column(String, primary_key=True)
    work_id: Mapped[str | None] = mapped_column(String, nullable=True)

class Book(Base, TimestampMixin, LastSyncedMixin):
    __tablename__ = 'book'

    goodreads_id: Mapped[str] = mapped_column(String, primary_key=True)
    work_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    published_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    published_state: Mapped[str | None] = mapped_column(String, nullable=True)
    language: Mapped[str | None] = mapped_column(String, nullable=True)
    calibre_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    isbn: Mapped[str | None] = mapped_column(String, nullable=True)
    goodreads_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    goodreads_votes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    similar_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    book_authors = relationship('BookAuthor', back_populates='book')
    book_genres = relationship('BookGenre', back_populates='book')
    book_users = relationship('BookUser', back_populates='book')
    book_series = relationship('BookSeries', back_populates='book')
    library_entries = relationship('Library', back_populates='book')
    similar_to = relationship('BookSimilar', foreign_keys=[BookSimilar.work_id], back_populates='book')
    similar_books = relationship('BookSimilar', foreign_keys=[BookSimilar.similar_work_id], back_populates='similar_book')

    # Convenience relationships
    authors = relationship('Author', secondary='book_author', viewonly=True)
    genres = relationship('Genre', secondary='book_genre', viewonly=True)
    users = relationship('User', secondary='book_user', viewonly=True)
    series = relationship('Series', secondary='book_series', viewonly=True)