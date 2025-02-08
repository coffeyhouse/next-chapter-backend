# core/sqlalchemy/__init__.py
from .database import Database
from .models import (
    Base, Book, Author, Series, Genre,
    Library, User, book_author, book_genre,
    book_series, book_similar, book_user
)

__all__ = [
    'Database',
    'Base',
    'Book',
    'Author',
    'Series',
    'Genre',
    'Library',
    'User',
    'book_author',
    'book_genre',
    'book_series',
    'book_similar',
    'book_user'
]