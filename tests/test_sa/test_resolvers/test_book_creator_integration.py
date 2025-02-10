import pytest
from datetime import datetime
from core.resolvers.book_creator import BookCreator
from core.resolvers.book_resolver import BookResolver
from core.sa.models import Book

@pytest.fixture
def book_creator(db_session):
    return BookCreator(db_session, scrape=True)  # Enable real scraping

@pytest.fixture
def book_resolver():
    return BookResolver(scrape=True)  # Enable real scraping

def test_create_book_from_real_data(book_creator, book_resolver, db_session):
    """Integration test using real data from Goodreads"""
    # Project Hail Mary by Andy Weir
    goodreads_id = '54493401'
    
    # First get the real book data
    book_data = book_resolver.resolve_book(goodreads_id)
    assert book_data is not None, "Failed to resolve book data"
    
    # Create the book
    book = book_creator.create_book(book_data)
    
    # Basic book data verification
    assert book is not None
    assert book.goodreads_id == goodreads_id
    assert book.title == "Project Hail Mary"
    assert book.work_id is not None
    assert book.language == "English"
    assert book.pages is not None
    assert book.isbn is not None
    assert book.goodreads_rating is not None
    assert book.goodreads_votes is not None
    assert book.description is not None
    assert book.image_url is not None
    
    # Verify relationships
    assert len(book.authors) > 0
    assert any(author.name == "Andy Weir" for author in book.authors)
    
    assert len(book.genres) > 0
    expected_genres = {"Science Fiction", "Fiction"}
    found_genres = {genre.name for genre in book.genres}
    assert any(genre in found_genres for genre in expected_genres)
    
    # Verify persistence
    db_session.expire_all()
    book = db_session.query(Book).filter_by(goodreads_id=goodreads_id).first()
    assert book is not None
    assert len(book.authors) > 0
    assert len(book.genres) > 0

def test_create_book_from_real_data_with_series(book_creator, book_resolver, db_session):
    """Integration test using real data from a book that's part of a series"""
    # The Way of Kings by Brandon Sanderson
    goodreads_id = '7235533'
    
    # First get the real book data
    book_data = book_resolver.resolve_book(goodreads_id)
    assert book_data is not None, "Failed to resolve book data"
    
    # Create the book
    book = book_creator.create_book(book_data)
    
    # Basic book data verification
    assert book is not None
    assert book.goodreads_id == goodreads_id
    assert book.title == "The Way of Kings"
    assert book.work_id is not None
    
    # Verify relationships
    assert len(book.authors) > 0
    assert any(author.name == "Brandon Sanderson" for author in book.authors)
    
    assert len(book.genres) > 0
    expected_genres = {"Fantasy", "Fiction"}
    found_genres = {genre.name for genre in book.genres}
    assert any(genre in found_genres for genre in expected_genres)
    
    # Verify series
    assert len(book.series) > 0
    assert any("Stormlight Archive" in series.title for series in book.series)
    
    # Verify persistence
    db_session.expire_all()
    book = db_session.query(Book).filter_by(goodreads_id=goodreads_id).first()
    assert book is not None
    assert len(book.authors) > 0
    assert len(book.genres) > 0
    assert len(book.series) > 0 