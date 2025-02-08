# tests/sqlalchemy/test_models.py
import pytest
from core.sqlalchemy.models import Book, Author, Genre, Series

def test_book_model_exists(db_session):
    """Test that we can query the book table"""
    # Get book count
    count = db_session.query(Book).count()
    assert count > 0, "Book table should not be empty"
    
    # Get one book and check its structure
    book = db_session.query(Book).first()
    assert book is not None
    assert hasattr(book, 'title')
    assert hasattr(book, 'goodreads_id')
    assert hasattr(book, 'work_id')

def test_book_relationships(db_session):
    """Test that book relationships are properly configured"""
    # Get a book that has authors and genres
    book = db_session.query(Book).join(Book.authors).join(Book.genres).first()
    assert book is not None
    
    # Check authors
    assert len(book.authors) > 0, "Book should have at least one author"
    author = book.authors[0]
    assert hasattr(author, 'name')
    assert hasattr(author, 'goodreads_id')
    
    # Check genres
    if book.genres:  # Some books might not have genres
        genre = book.genres[0]
        assert hasattr(genre, 'name')