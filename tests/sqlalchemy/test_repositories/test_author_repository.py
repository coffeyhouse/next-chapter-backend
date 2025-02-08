# tests/sqlalchemy/test_repositories/test_author_repository.py
import pytest
from datetime import datetime, timedelta, UTC
from sqlalchemy import func
from core.sqlalchemy.repositories.author import AuthorRepository
from core.sqlalchemy.models import Author, Book

@pytest.fixture
def author_repo(db_session):
    """Fixture to create an AuthorRepository instance"""
    return AuthorRepository(db_session)

def test_get_by_goodreads_id(author_repo, db_session):
    """Test fetching an author by Goodreads ID"""
    # Get first author's ID for testing
    author = db_session.query(Author).first()
    assert author is not None
    
    # Test repository method
    fetched_author = author_repo.get_by_goodreads_id(author.goodreads_id)
    assert fetched_author is not None
    assert fetched_author.goodreads_id == author.goodreads_id
    assert fetched_author.name == author.name

def test_get_by_nonexistent_goodreads_id(author_repo):
    """Test fetching with non-existent Goodreads ID"""
    author = author_repo.get_by_goodreads_id("nonexistent_id")
    assert author is None

def test_search_authors(author_repo, db_session):
    """Test author search functionality"""
    # Get an author name to search for
    author = db_session.query(Author).first()
    search_term = author.name.split()[0]  # Use first word of name
    
    # Test search
    results = author_repo.search_authors(search_term)
    assert len(results) > 0
    assert any(author.name in result.name for result in results)

def test_search_authors_with_empty_query(author_repo):
    """Test search with empty query"""
    results = author_repo.search_authors("")
    assert len(results) == 20  # Default limit

def test_search_authors_with_limit(author_repo):
    """Test search with custom limit"""
    limit = 5
    results = author_repo.search_authors("a", limit=limit)  # 'a' should match many names
    assert len(results) <= limit

def test_get_recent_authors(author_repo):
    """Test getting recently added authors"""
    limit = 5
    authors = author_repo.get_recent_authors(limit=limit)
    assert len(authors) <= limit
    # Verify authors are in correct order
    for i in range(len(authors) - 1):
        assert authors[i].created_at >= authors[i + 1].created_at

def test_get_authors_by_book(author_repo, db_session):
    """Test getting authors for a specific book"""
    # Get a book that has authors
    book = db_session.query(Book).join(Book.authors).first()
    assert book is not None
    
    # Test repository method
    authors = author_repo.get_authors_by_book(book.goodreads_id)
    assert len(authors) > 0
    assert all(book in author.books for author in authors)

def test_get_unsynced_authors(author_repo, db_session):
    """Test getting unsynced authors"""
    days_old = 30
    authors = author_repo.get_unsynced_authors(days_old)
    cutoff_date = datetime.now(UTC) - timedelta(days=days_old)
    
    # Verify the query returns results
    assert len(authors) > 0
    
    # Verify all returned authors are either never synced or synced before cutoff
    for author in authors:
        assert hasattr(author, 'last_synced_at'), "Author missing last_synced_at field"
        assert (author.last_synced_at is None or 
                author.last_synced_at < cutoff_date)

def test_get_prolific_authors(author_repo, db_session):
    """Test getting authors with multiple books"""
    min_books = 2
    authors = author_repo.get_prolific_authors(min_books=min_books)
    
    # Verify each author has at least min_books
    for author in authors:
        assert len(author.books) >= min_books

def test_get_authors_by_nonexistent_book(author_repo):
    """Test getting authors for non-existent book"""
    authors = author_repo.get_authors_by_book("nonexistent_id")
    assert len(authors) == 0