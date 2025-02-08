# tests/test_sa/test_repositories/test_genre_repository.py

import pytest
from datetime import datetime, timedelta, UTC
from core.sa.repositories.genre import GenreRepository
from core.sa.models import Genre, Book

@pytest.fixture
def genre_repo(db_session):
    """Fixture to create a GenreRepository instance."""
    return GenreRepository(db_session)

@pytest.fixture
def sample_genre(db_session):
    """Fixture to create and return a sample Genre object."""
    genre = Genre(name="Test Genre")
    db_session.add(genre)
    db_session.commit()
    return genre

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
def genre_with_book(db_session, sample_genre, sample_book):
    """Fixture to associate a sample Genre with a Book."""
    sample_genre.books.append(sample_book)
    db_session.commit()
    return sample_genre

def test_get_by_name(genre_repo, db_session):
    """Test fetching a genre by its name."""
    genre = Genre(name="Fantasy")
    db_session.add(genre)
    db_session.commit()

    fetched = genre_repo.get_by_name("Fantasy")
    assert fetched is not None
    assert fetched.name == "Fantasy"

def test_get_by_nonexistent_name(genre_repo):
    """Test fetching a genre with non-existent name."""
    result = genre_repo.get_by_name("Nonexistent Genre")
    assert result is None

def test_search_genres(genre_repo, db_session):
    """Test searching for genres by name."""
    genres = [
        Genre(name="Science Fiction"),
        Genre(name="Science Fantasy"),
        Genre(name="Horror")
    ]
    db_session.add_all(genres)
    db_session.commit()

    results = genre_repo.search_genres("Science")
    names = [g.name for g in results]
    assert "Science Fiction" in names
    assert "Science Fantasy" in names
    assert "Horror" not in names

def test_search_genres_empty_query(genre_repo, db_session):
    """Test search behavior with empty query."""
    genres = [Genre(name=f"Genre {i}") for i in range(3)]
    db_session.add_all(genres)
    db_session.commit()

    results = genre_repo.search_genres("")
    assert len(results) <= 20  # Default limit
    assert all(isinstance(g, Genre) for g in results)

def test_search_genres_with_limit(genre_repo, db_session):
    """Test search respects the limit parameter."""
    genres = [Genre(name=f"Test Genre {i}") for i in range(5)]
    db_session.add_all(genres)
    db_session.commit()

    results = genre_repo.search_genres("Test", limit=3)
    assert len(results) == 3

def test_search_genres_special_characters(genre_repo, db_session):
    """Test searching with special characters."""
    special_name = "Sci-Fi & Fantasy"
    genre = Genre(name=special_name)
    db_session.add(genre)
    db_session.commit()

    results = genre_repo.search_genres("&")
    assert len(results) == 1
    assert results[0].name == special_name

def test_get_genres_by_book(genre_repo, db_session, sample_book):
    """Test retrieving genres associated with a book."""
    genres = [
        Genre(name="Genre 1"),
        Genre(name="Genre 2")
    ]
    for genre in genres:
        genre.books.append(sample_book)
    db_session.add_all(genres)
    db_session.commit()

    results = genre_repo.get_genres_by_book(sample_book.goodreads_id)
    names = [g.name for g in results]
    assert "Genre 1" in names
    assert "Genre 2" in names

def test_get_genres_by_nonexistent_book(genre_repo):
    """Test getting genres for a non-existent book."""
    results = genre_repo.get_genres_by_book("nonexistent_book")
    assert len(results) == 0

def test_get_popular_genres(genre_repo, db_session):
    """Test getting popular genres based on book count."""
    # Create genres and books
    genres = [Genre(name=f"Genre {i}") for i in range(3)]
    books = [
        Book(goodreads_id=f"book_{i}", work_id=f"work_{i}", title=f"Book {i}")
        for i in range(4)
    ]
    db_session.add_all(genres + books)
    db_session.commit()

    # Add different numbers of books to each genre
    genres[0].books.extend(books[0:3])  # 3 books
    genres[1].books.extend(books[1:4])  # 3 books
    genres[2].books.append(books[0])    # 1 book
    db_session.commit()

    results = genre_repo.get_popular_genres(limit=2)
    assert len(results) == 2
    # Both genres with 3 books should be before the genre with 1 book
    assert len(results[0].books) == 3
    assert len(results[1].books) == 3

def test_get_recent_genres(genre_repo, db_session):
    """Test fetching recently added genres."""
    now = datetime.now(UTC)
    genre_old = Genre(name="Old Genre")
    genre_recent = Genre(name="Recent Genre")
    
    genre_old.created_at = now - timedelta(days=10)
    genre_recent.created_at = now

    db_session.add_all([genre_old, genre_recent])
    db_session.commit()

    results = genre_repo.get_recent_genres(limit=2)
    assert results[0].name == "Recent Genre"
    assert results[1].name == "Old Genre"

def test_get_recent_genres_with_limit(genre_repo, db_session):
    """Test recent genres respects the limit parameter."""
    genres = [Genre(name=f"Recent Genre {i}") for i in range(5)]
    db_session.add_all(genres)
    db_session.commit()

    results = genre_repo.get_recent_genres(limit=3)
    assert len(results) == 3

def test_merge_genres(genre_repo, db_session):
    """Test merging one genre into another."""
    # Create source and target genres with books
    source = Genre(name="Sci-Fi")
    target = Genre(name="Science Fiction")
    books = [
        Book(goodreads_id=f"book_{i}", work_id=f"work_{i}", title=f"Book {i}")
        for i in range(2)
    ]
    
    source.books.append(books[0])
    target.books.append(books[1])
    
    db_session.add_all([source, target] + books)
    db_session.commit()

    # Perform merge
    result = genre_repo.merge_genres("Sci-Fi", "Science Fiction")
    assert result is not None
    assert result.name == "Science Fiction"
    
    # Verify source genre no longer exists
    assert genre_repo.get_by_name("Sci-Fi") is None
    
    # Verify all books are now associated with target genre
    target = genre_repo.get_by_name("Science Fiction")
    assert len(target.books) == 2
    book_ids = [b.goodreads_id for b in target.books]
    assert "book_0" in book_ids
    assert "book_1" in book_ids

def test_merge_nonexistent_genres(genre_repo, db_session):
    """Test merging with non-existent genres."""
    target = Genre(name="Target Genre")
    db_session.add(target)
    db_session.commit()

    # Try to merge non-existent source
    result = genre_repo.merge_genres("Nonexistent", "Target Genre")
    assert result is None

    # Try to merge into non-existent target
    result = genre_repo.merge_genres("Target Genre", "Nonexistent")
    assert result is None 