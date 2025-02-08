# core/sa/repositories/__init__.py
from .book import BookRepository
from .author import AuthorRepository

__all__ = ['BookRepository', 'AuthorRepository']