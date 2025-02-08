# tests/sqlalchemy/test_repositories/test_book_repository.py
import pytest
from datetime import datetime
from sqlalchemy import select
from core.sqlalchemy.repositories import BookRepository
from core.sqlalchemy.models import Book, Author, Genre, Series

@pytest.fixture
def book_repo(db_session):
    """Fixture to create a BookRepository instance"""
    return BookRepository(db_session)

def test_get_by_goodreads_id(book_repo, db_session):
    """Test fetching a book by Goodreads ID"""
    # Get first book's ID for testing
    book = db_session.query(Book).first()
    assert book is not None
    
    # Test repository method
    fetched_book = book_repo.get_by_goodreads_id(book.goodreads_id)
    assert fetched_book is not None
    assert fetched_book.goodreads_id == book.goodreads_id
    assert fetched_book.title == book.title

def test_get_by_nonexistent_goodreads_id(book_repo):
    """Test fetching a book with a non-existent Goodreads ID"""
    book = book_repo.get_by_goodreads_id("nonexistent_id")
    assert book is None

def test_search_books(book_repo, db_session):
    """Test book search functionality"""
    # Get a book title to search for
    book = db_session.query(Book).first()
    search_term = book.title.split()[0]  # Use first word of title
    
    # Test search
    results = book_repo.search_books(search_term)
    assert len(results) > 0
    assert any(book.title in result.title for result in results)

def test_search_books_with_empty_query(book_repo):
    """Test search with empty query"""
    results = book_repo.search_books("")
    assert len(results) == 20  # Default limit

def test_search_books_with_limit(book_repo):
    """Test search with custom limit"""
    limit = 5
    results = book_repo.search_books("the", limit=limit)
    assert len(results) <= limit

def test_get_books_by_author(book_repo, db_session):
    """Test getting books by author"""
    # Get an author who has books
    author = db_session.query(Author).join(Author.books).first()
    assert author is not None
    
    # Test repository method
    books = book_repo.get_books_by_author(author.goodreads_id)
    assert len(books) > 0
    assert all(author in book.authors for book in books)

def test_get_books_by_nonexistent_author(book_repo):
    """Test getting books for non-existent author"""
    books = book_repo.get_books_by_author("nonexistent_author")
    assert len(books) == 0

def test_get_books_by_genre(book_repo, db_session):
    """Test getting books by genre"""
    # Get a genre that has books
    genre = db_session.query(Genre).join(Genre.books).first()
    assert genre is not None
    
    # Test repository method
    books = book_repo.get_books_by_genre(genre.name)
    assert len(books) > 0
    assert all(genre in book.genres for book in books)

def test_get_books_by_nonexistent_genre(book_repo):
    """Test getting books for non-existent genre"""
    books = book_repo.get_books_by_genre("nonexistent_genre")
    assert len(books) == 0

def test_get_books_with_rating_above(book_repo, db_session):
    """Test getting books with rating above threshold"""
    min_rating = 4.0
    books = book_repo.get_books_with_rating_above(min_rating)
    assert all(book.goodreads_rating >= min_rating for book in books)

def test_get_recent_books(book_repo):
    """Test getting recently added books"""
    limit = 5
    books = book_repo.get_recent_books(limit=limit)
    assert len(books) <= limit
    # Verify books are in correct order
    for i in range(len(books) - 1):
        assert books[i].created_at >= books[i + 1].created_at

def test_get_books_in_series(book_repo, db_session):
    """Test getting books in a series"""
    # Get a series that has books
    series = db_session.query(Series).join(Series.books).first()
    assert series is not None
    
    # Test repository method
    books = book_repo.get_books_in_series(series.goodreads_id)
    assert len(books) > 0
    assert all(series in book.series for book in books)

def test_get_similar_books(book_repo, db_session):
    """Test getting similar books"""
    # Get a book that has similar books
    book = db_session.query(Book).filter(Book.similar_books.any()).first()
    if book is not None:  # Some books might not have similar books
        similar_books = book_repo.get_similar_books(book.work_id)
        assert len(similar_books) > 0
        # Verify these are actually marked as similar
        assert all(similar in book.similar_books for similar in similar_books)

def test_get_books_with_filters(book_repo):
    """Test getting books with multiple filters"""
    filters = {
        'min_rating': 4.0,
        'min_votes': 1000,
        'language': 'English'
    }
    books = book_repo.get_books_with_filters(**filters)
    assert all(
        book.goodreads_rating >= filters['min_rating'] and
        book.goodreads_votes >= filters['min_votes'] and
        book.language == filters['language']
        for book in books
    )