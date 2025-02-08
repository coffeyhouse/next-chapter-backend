# tests/test_sa/test_models.py
import pytest
from core.sa.models import (
    Base, Book, Author, Genre, Series, BookSeries,
    BookAuthor, BookGenre, BookSimilar, User, BookUser
)

def test_book_model_exists(db_session, sample_book):
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

def test_book_relationships(db_session, sample_book_with_relationships):
    """Test that book relationships are properly configured"""
    # Get a book with its relationships
    book = db_session.query(Book).filter_by(work_id="work_1").first()
    assert book is not None
    
    # Check authors through association model
    assert len(book.book_authors) > 0, "Book should have at least one book_author relationship"
    book_author = book.book_authors[0]
    assert hasattr(book_author, 'role')
    assert book_author.author.name == "Test Author"
    
    # Check convenience relationship
    assert len(book.authors) > 0, "Book should have at least one author"
    author = book.authors[0]
    assert hasattr(author, 'name')
    assert hasattr(author, 'goodreads_id')
    
    # Check genres through association model
    assert len(book.book_genres) > 0, "Book should have at least one book_genre relationship"
    book_genre = book.book_genres[0]
    assert book_genre.genre.name == "Test Genre"
    
    # Check convenience relationship
    assert len(book.genres) > 0, "Book should have at least one genre"
    genre = book.genres[0]
    assert hasattr(genre, 'name')
    
    # Check series through association model
    assert len(book.book_series) > 0, "Book should have at least one book_series relationship"
    book_series = book.book_series[0]
    assert hasattr(book_series, 'series_order')
    assert book_series.series.title == "Test Series"
    
    # Check convenience relationship
    assert len(book.series) > 0, "Book should have at least one series"
    series = book.series[0]
    assert hasattr(series, 'title')
    
    # Check similar books through association model
    assert len(book.similar_to) > 0, "Book should have at least one similar book relationship"
    book_similar = book.similar_to[0]
    assert book_similar.similar_book.title == "Similar Test Book"

def test_author_relationships(db_session, sample_book_with_relationships):
    """Test that author relationships are properly configured"""
    author = db_session.query(Author).filter_by(goodreads_id="author_1").first()
    assert author is not None
    
    # Check books through association model
    assert len(author.book_authors) > 0, "Author should have at least one book_author relationship"
    book_author = author.book_authors[0]
    assert hasattr(book_author, 'role')
    assert book_author.book.title == "Test Book"
    
    # Check convenience relationship
    assert len(author.books) > 0, "Author should have at least one book"
    book = author.books[0]
    assert hasattr(book, 'title')
    assert hasattr(book, 'work_id')

def test_genre_relationships(db_session, sample_book_with_relationships):
    """Test that genre relationships are properly configured"""
    genre = db_session.query(Genre).filter_by(name="Test Genre").first()
    assert genre is not None
    
    # Check books through association model
    assert len(genre.book_genres) > 0, "Genre should have at least one book_genre relationship"
    book_genre = genre.book_genres[0]
    assert book_genre.book.title == "Test Book"
    
    # Check convenience relationship
    assert len(genre.books) > 0, "Genre should have at least one book"
    book = genre.books[0]
    assert hasattr(book, 'title')
    assert hasattr(book, 'work_id')

def test_series_relationships(db_session, sample_book_with_relationships):
    """Test that series relationships are properly configured"""
    series = db_session.query(Series).filter_by(goodreads_id="series_1").first()
    assert series is not None
    
    # Check books through association model
    assert len(series.book_series) > 0, "Series should have at least one book_series relationship"
    book_series = series.book_series[0]
    assert hasattr(book_series, 'series_order')
    assert book_series.book.title == "Test Book"
    
    # Check convenience relationship
    assert len(series.books) > 0, "Series should have at least one book"
    book = series.books[0]
    assert hasattr(book, 'title')
    assert hasattr(book, 'work_id')