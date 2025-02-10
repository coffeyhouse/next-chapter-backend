# tests/test_sa/conftest.py
import os
import sys
import pytest
from pathlib import Path
from sqlalchemy.sql import text
from datetime import datetime, UTC, timedelta

# Add debugging information
print("\nCurrent working directory:", os.getcwd())
print("__file__:", __file__)

# Calculate project root
project_root = str(Path(__file__).parent.parent.parent)
print("Project root path:", project_root)
print("Current sys.path:", sys.path)

# Add project root to Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    print("Updated sys.path:", sys.path)

try:
    from sqlalchemy.orm import Session
    print("Successfully imported sqlalchemy.orm")
except ImportError as e:
    print("Failed to import sqlalchemy.orm:", str(e))
    
try:
    from core.sa.models import (
        Base, Book, Author, Genre, Series, BookSeries,
        BookAuthor, BookGenre, BookSimilar, User, BookUser
    )
    print("Successfully imported core.sa.models")
except ImportError as e:
    print("Failed to import core.sa.models:", str(e))
    
try:
    from core.sa.database import Database
    print("Successfully imported core.sa.database")
except ImportError as e:
    print("Failed to import core.sa.database:", str(e))

@pytest.fixture(scope="session")
def test_db_path(tmp_path_factory):
    """Create a temporary directory for the test database."""
    test_dir = tmp_path_factory.mktemp("test_db")
    return str(test_dir / "test_books.db")

@pytest.fixture(scope="session")
def database(test_db_path):
    """Create a test database instance"""
    db = Database(db_path=test_db_path)
    
    # Drop all tables and recreate schema
    Base.metadata.drop_all(db.engine)
    Base.metadata.create_all(db.engine)
    
    yield db
    
    # Clean up the test database file after all tests
    try:
        os.remove(test_db_path)
    except OSError:
        pass  # Ignore errors if file doesn't exist

@pytest.fixture(autouse=True)
def cleanup_db(db_session):
    """Clean up database tables before each test"""
    # Delete all data from tables in reverse order of dependencies
    db_session.execute(text("DELETE FROM book_similar"))
    db_session.execute(text("DELETE FROM book_series"))
    db_session.execute(text("DELETE FROM book_genre"))
    db_session.execute(text("DELETE FROM book_author"))
    db_session.execute(text("DELETE FROM book_user"))
    db_session.execute(text("DELETE FROM library"))
    db_session.execute(text("DELETE FROM series"))
    db_session.execute(text("DELETE FROM book"))
    db_session.execute(text("DELETE FROM author"))
    db_session.execute(text("DELETE FROM genre"))
    db_session.execute(text("DELETE FROM user"))
    db_session.commit()
    yield
    # Clean up after test as well
    db_session.rollback()

@pytest.fixture(scope="function")
def db_session(database):
    """Create a new database session for a test"""
    session: Session = database._SessionFactory()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def sample_author(db_session):
    """Create a sample author for testing."""
    author = Author(
        goodreads_id="author_1",
        name="Test Author",
        bio="Test author description",
        image_url="http://example.com/author.jpg"
    )
    db_session.add(author)
    db_session.commit()
    return author

@pytest.fixture
def sample_genre(db_session):
    """Create a sample genre for testing."""
    genre = Genre(
        name="Test Genre"
    )
    db_session.add(genre)
    db_session.commit()
    return genre

@pytest.fixture
def sample_series(db_session):
    """Create a sample series for testing."""
    series = Series(
        goodreads_id="series_1",
        title="Test Series"
    )
    db_session.add(series)
    db_session.commit()
    return series

@pytest.fixture
def sample_book(db_session):
    """Create a sample book for testing."""
    book = Book(
        goodreads_id="book_1",
        work_id="work_1",
        title="Test Book",
        published_date=datetime.now(UTC),
        language="English",
        pages=200,
        isbn="1234567890",
        goodreads_rating=4.5,
        goodreads_votes=1000,
        description="Test book description"
    )
    db_session.add(book)
    db_session.commit()
    return book

@pytest.fixture
def sample_book_with_relationships(db_session, sample_book, sample_author, sample_genre, sample_series):
    """Create a book with all relationships for testing."""
    # Add author relationship
    book_author = BookAuthor(
        work_id=sample_book.work_id,
        author_id=sample_author.goodreads_id,
        role="author"
    )
    db_session.add(book_author)
    
    # Add genre relationship
    book_genre = BookGenre(
        work_id=sample_book.work_id,
        genre_id=sample_genre.id
    )
    db_session.add(book_genre)
    
    # Create book-series relationship with order
    book_series = BookSeries(
        work_id=sample_book.work_id,
        series_id=sample_series.goodreads_id,
        series_order=1.0
    )
    db_session.add(book_series)
    
    # Add similar book
    similar_book = Book(
        goodreads_id="book_2",
        work_id="work_2",
        title="Similar Test Book",
        published_date=datetime.now(UTC)
    )
    db_session.add(similar_book)
    
    # Add similar book relationship
    book_similar = BookSimilar(
        work_id=sample_book.work_id,
        similar_work_id=similar_book.work_id
    )
    db_session.add(book_similar)
    
    db_session.commit()
    return sample_book

@pytest.fixture
def multiple_books(db_session, sample_genre, sample_series):
    """Create multiple books with relationships for testing."""
    books = []
    for i in range(1, 21):  # Create 20 books
        # Create a unique author for each book
        author = Author(
            goodreads_id=f"author_{i}",
            name=f"Test Author {i}",
            bio=f"Test author {i} description",
            image_url=f"http://example.com/author_{i}.jpg"
        )
        db_session.add(author)
        
        book = Book(
            goodreads_id=f"book_{i}",
            work_id=f"work_{i}",
            title=f"Test Book {i}",
            published_date=datetime.now(UTC),
            goodreads_rating=4.0 + (i % 10) / 10,  # Ratings from 4.0 to 4.9
            goodreads_votes=i * 100
        )
        db_session.add(book)
        
        # Add author relationship
        book_author = BookAuthor(
            work_id=book.work_id,
            author_id=author.goodreads_id,
            role="author"
        )
        db_session.add(book_author)
        
        # Add genre relationship
        book_genre = BookGenre(
            work_id=book.work_id,
            genre_id=sample_genre.id
        )
        db_session.add(book_genre)
        
        # Add to series with order
        book_series = BookSeries(
            work_id=book.work_id,
            series_id=sample_series.goodreads_id,
            series_order=float(i)
        )
        db_session.add(book_series)
        
        books.append(book)
    
    db_session.commit()
    return books

@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing."""
    user = User(name="Test User")
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def sample_user_with_books(db_session, sample_user, sample_book):
    """Create a user with book relationships for testing."""
    book_user = BookUser(
        work_id=sample_book.work_id,
        user_id=sample_user.id,
        status="reading",
        source="test",
        started_at=datetime.now(UTC)
    )
    db_session.add(book_user)
    db_session.commit()
    return sample_user

@pytest.fixture
def multiple_users_with_books(db_session, multiple_books):
    """Create multiple users with book relationships for testing."""
    users = []
    statuses = ["reading", "completed", "want_to_read"]
    
    for i in range(5):  # Create 5 users
        user = User(name=f"Test User {i}")
        db_session.add(user)
        db_session.commit()
        
        # Associate each user with some books
        for j, book in enumerate(multiple_books[:3]):  # First 3 books
            book_user = BookUser(
                work_id=book.work_id,
                user_id=user.id,
                status=statuses[j % len(statuses)],
                source="test",
                started_at=datetime.now(UTC) - timedelta(days=i)
            )
            if book_user.status == "completed":
                book_user.finished_at = datetime.now(UTC)
            db_session.add(book_user)
        
        users.append(user)
    
    db_session.commit()
    return users