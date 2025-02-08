# tests/test_sa/test_repositories/test_series_repository.py

import pytest
from datetime import datetime, timedelta, UTC
from core.sa.repositories.series import SeriesRepository
from core.sa.models import Series, Book, BookSeries

@pytest.fixture
def series_repo(db_session):
    """Fixture to create a SeriesRepository instance."""
    return SeriesRepository(db_session)

@pytest.fixture
def sample_series(db_session):
    """Fixture to create and return a sample Series object."""
    series = Series(goodreads_id="series_1", title="Test Series")
    db_session.add(series)
    db_session.commit()
    return series

@pytest.fixture
def sample_book(db_session):
    """Fixture to create and return a sample Book object."""
    book = Book(
        goodreads_id="book_1",
        work_id="work_1",
        title="Test Book"
    )
    db_session.add(book)
    db_session.commit()
    return book

@pytest.fixture
def series_with_book(db_session, sample_series, sample_book):
    """Fixture to associate a sample Series with a Book."""
    book_series = BookSeries(
        work_id=sample_book.work_id,
        series_id=sample_series.goodreads_id,
        series_order=1.0
    )
    db_session.add(book_series)
    db_session.commit()
    return sample_series

@pytest.fixture
def series_with_multiple_books(db_session):
    """Fixture to create a series with multiple books in specific order."""
    series = Series(goodreads_id="multi_book_series", title="Multiple Books Series")
    books = [
        Book(goodreads_id=f"book_{i}", work_id=f"work_{i}", title=f"Book {i}")
        for i in range(1, 4)
    ]
    db_session.add_all([series] + books)
    db_session.commit()

    # Add books to series with specific order
    for i, book in enumerate(books, 1):
        book_series = BookSeries(
            work_id=book.work_id,
            series_id=series.goodreads_id,
            series_order=float(i)
        )
        db_session.add(book_series)
    
    db_session.commit()
    return series, books

def test_get_by_goodreads_id(series_repo, db_session):
    """Test fetching a series by its Goodreads ID."""
    test_series = Series(goodreads_id="series_test", title="Sample Series")
    db_session.add(test_series)
    db_session.commit()

    fetched = series_repo.get_by_goodreads_id("series_test")
    assert fetched is not None
    assert fetched.goodreads_id == "series_test"
    assert fetched.title == "Sample Series"

def test_get_by_nonexistent_goodreads_id(series_repo):
    """Test fetching a series with non-existent Goodreads ID."""
    result = series_repo.get_by_goodreads_id("nonexistent_id")
    assert result is None

def test_search_series(series_repo, db_session):
    """Test searching for series by title."""
    series1 = Series(goodreads_id="series_search_1", title="Amazing Series")
    series2 = Series(goodreads_id="series_search_2", title="Another Amazing Series")
    db_session.add_all([series1, series2])
    db_session.commit()

    results = series_repo.search_series("Amazing")
    titles = [s.title for s in results]
    assert "Amazing Series" in titles
    assert "Another Amazing Series" in titles

def test_search_series_empty_query(series_repo, db_session):
    """Test search behavior with empty query."""
    # Add some series to ensure we have data
    series_list = [
        Series(goodreads_id=f"series_{i}", title=f"Series {i}")
        for i in range(3)
    ]
    db_session.add_all(series_list)
    db_session.commit()

    results = series_repo.search_series("")
    assert len(results) <= 20  # Default limit
    assert all(isinstance(s, Series) for s in results)

def test_search_series_with_limit(series_repo, db_session):
    """Test search respects the limit parameter."""
    # Create more series than the limit
    series_list = [
        Series(goodreads_id=f"series_{i}", title=f"Test Series {i}")
        for i in range(5)
    ]
    db_session.add_all(series_list)
    db_session.commit()

    results = series_repo.search_series("Test", limit=3)
    assert len(results) == 3

def test_search_series_special_characters(series_repo, db_session):
    """Test searching with special characters."""
    special_title = "Series with & and % characters!"
    series = Series(goodreads_id="special_chars", title=special_title)
    db_session.add(series)
    db_session.commit()

    results = series_repo.search_series("&")
    assert len(results) == 1
    assert results[0].title == special_title

def test_get_series_with_books(series_repo, db_session, sample_book):
    """Test retrieving a series along with its associated books."""
    test_series = Series(goodreads_id="series_with_books", title="Series With Books")
    db_session.add(test_series)
    db_session.commit()

    book_series = BookSeries(
        work_id=sample_book.work_id,
        series_id=test_series.goodreads_id,
        series_order=1.0
    )
    db_session.add(book_series)
    db_session.commit()

    fetched = series_repo.get_series_with_books("series_with_books")
    assert fetched is not None
    assert any(book.goodreads_id == sample_book.goodreads_id for book in fetched.books)

def test_get_series_with_ordered_books(series_repo, series_with_multiple_books, db_session):
    """Test that books in a series maintain their order."""
    series, books = series_with_multiple_books
    
    fetched = series_repo.get_series_with_books(series.goodreads_id)
    assert fetched is not None
    
    # Get the book_series associations to check order
    book_series_list = db_session.query(BookSeries).filter_by(series_id=series.goodreads_id).all()
    
    # Verify order is maintained
    for i, book_series in enumerate(book_series_list, 1):
        assert book_series.series_order == float(i)

def test_get_series_by_book(series_repo, db_session, sample_book):
    """Test retrieving series that include a specific book."""
    series1 = Series(goodreads_id="series_by_book_1", title="Series One")
    series2 = Series(goodreads_id="series_by_book_2", title="Series Two")
    db_session.add_all([series1, series2])
    db_session.commit()

    # Create book-series associations
    book_series1 = BookSeries(
        work_id=sample_book.work_id,
        series_id=series1.goodreads_id,
        series_order=1.0
    )
    book_series2 = BookSeries(
        work_id=sample_book.work_id,
        series_id=series2.goodreads_id,
        series_order=1.0
    )
    db_session.add_all([book_series1, book_series2])
    db_session.commit()

    results = series_repo.get_series_by_book(sample_book.goodreads_id)
    series_ids = [s.goodreads_id for s in results]
    assert "series_by_book_1" in series_ids
    assert "series_by_book_2" in series_ids

def test_get_series_by_nonexistent_book(series_repo):
    """Test getting series for a non-existent book."""
    results = series_repo.get_series_by_book("nonexistent_book")
    assert len(results) == 0

def test_get_recent_series(series_repo, db_session):
    """Test fetching the most recently added series."""
    now = datetime.now(UTC)
    series_old = Series(goodreads_id="series_old", title="Old Series")
    series_recent = Series(goodreads_id="series_recent", title="Recent Series")
    
    series_old.created_at = now - timedelta(days=10)
    series_recent.created_at = now

    db_session.add_all([series_old, series_recent])
    db_session.commit()

    results = series_repo.get_recent_series(limit=2)
    assert results[0].goodreads_id == "series_recent"
    assert results[1].goodreads_id == "series_old"

def test_get_recent_series_with_limit(series_repo, db_session):
    """Test recent series respects the limit parameter."""
    # Create more series than the limit
    series_list = [
        Series(goodreads_id=f"recent_{i}", title=f"Recent Series {i}")
        for i in range(5)
    ]
    db_session.add_all(series_list)
    db_session.commit()

    results = series_repo.get_recent_series(limit=3)
    assert len(results) == 3

def test_series_timestamps(series_repo, db_session):
    """Test that series timestamps are properly set and updated."""
    # Create a new series
    series = Series(goodreads_id="timestamp_test", title="Original Title")
    db_session.add(series)
    db_session.commit()
    
    original_created_at = series.created_at
    original_updated_at = series.updated_at
    
    # Wait a moment to ensure timestamp difference
    import time
    time.sleep(0.1)
    
    # Update the series
    series.title = "Updated Title"
    db_session.commit()
    
    # Verify timestamps
    assert series.created_at == original_created_at  # Should not change
    assert series.updated_at > original_updated_at  # Should be updated
