# tests/test_sa/test_repositories/test_user_repository.py

import pytest
from datetime import datetime, timedelta, UTC
from core.sa.repositories.user import UserRepository
from core.sa.models import User, Book, BookUser, Library

@pytest.fixture
def user_repo(db_session):
    """Fixture to create a UserRepository instance."""
    return UserRepository(db_session)

@pytest.fixture
def sample_user(db_session):
    """Fixture to create and return a sample User object."""
    user = User(name="Test User")
    db_session.add(user)
    db_session.commit()
    return user

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
def user_with_book(db_session, sample_user, sample_book):
    """Fixture to associate a sample User with a Book."""
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

def test_create_user(user_repo):
    """Test creating a new user."""
    user = user_repo.create_user(name="John Doe")
    assert user is not None
    assert user.name == "John Doe"
    assert user.id is not None

def test_create_duplicate_user(user_repo, sample_user):
    """Test that creating a user with a duplicate name raises an error."""
    with pytest.raises(ValueError, match="User with name 'Test User' already exists"):
        user_repo.create_user(name="Test User")

def test_create_user_case_sensitive(user_repo, sample_user):
    """Test that user names are case-sensitive."""
    # This should work since it's a different case
    user = user_repo.create_user(name="TEST USER")
    assert user is not None
    assert user.name == "TEST USER"

def test_update_user(user_repo, sample_user):
    """Test updating a user's name."""
    updated = user_repo.update_user(user_id=sample_user.id, name="Updated Name")
    assert updated is not None
    assert updated.name == "Updated Name"

def test_update_user_nonexistent(user_repo):
    """Test updating a non-existent user."""
    result = user_repo.update_user(user_id=999, name="New Name")
    assert result is None

def test_get_by_id(user_repo, sample_user):
    """Test fetching a user by their ID."""
    fetched = user_repo.get_by_id(sample_user.id)
    assert fetched is not None
    assert fetched.id == sample_user.id
    assert fetched.name == "Test User"

def test_get_by_nonexistent_id(user_repo):
    """Test fetching a user with non-existent ID."""
    result = user_repo.get_by_id(999)
    assert result is None

def test_search_users(user_repo, db_session):
    """Test searching for users by name."""
    users = [
        User(name="John Doe"),
        User(name="Jane Doe"),
        User(name="Alice Smith")
    ]
    db_session.add_all(users)
    db_session.commit()

    results = user_repo.search_users("Doe")
    names = [u.name for u in results]
    assert "John Doe" in names
    assert "Jane Doe" in names
    assert "Alice Smith" not in names

def test_search_users_empty_query(user_repo, db_session):
    """Test search behavior with empty query."""
    users = [User(name=f"User {i}") for i in range(3)]
    db_session.add_all(users)
    db_session.commit()

    results = user_repo.search_users("")
    assert len(results) <= 20  # Default limit
    assert all(isinstance(u, User) for u in results)

def test_search_users_with_limit(user_repo, db_session):
    """Test search respects the limit parameter."""
    users = [User(name=f"Test User {i}") for i in range(5)]
    db_session.add_all(users)
    db_session.commit()

    results = user_repo.search_users("Test", limit=3)
    assert len(results) == 3

def test_get_users_by_book(user_repo, db_session, sample_book):
    """Test retrieving users associated with a specific book."""
    users = [User(name=f"User {i}") for i in range(2)]
    db_session.add_all(users)
    db_session.commit()

    # Create book-user associations
    for user in users:
        book_user = BookUser(
            work_id=sample_book.work_id,
            user_id=user.id,
            status="reading"
        )
        db_session.add(book_user)
    db_session.commit()

    results = user_repo.get_users_by_book(sample_book.goodreads_id)
    assert len(results) == 2
    assert all(isinstance(u, User) for u in results)

def test_get_users_by_book_status(user_repo, db_session, sample_book):
    """Test retrieving users by book status."""
    users = [User(name=f"User {i}") for i in range(3)]
    db_session.add_all(users)
    db_session.commit()

    # Create book-user associations with different statuses
    statuses = ["reading", "completed", "reading"]
    for user, status in zip(users, statuses):
        book_user = BookUser(
            work_id=sample_book.work_id,
            user_id=user.id,
            status=status
        )
        db_session.add(book_user)
    db_session.commit()

    reading_users = user_repo.get_users_by_book_status("reading")
    assert len(reading_users) == 2

    completed_users = user_repo.get_users_by_book_status("completed")
    assert len(completed_users) == 1

def test_get_active_readers(user_repo, db_session, sample_book):
    """Test retrieving active readers."""
    now = datetime.now(UTC)
    users = [User(name=f"User {i}") for i in range(3)]
    db_session.add_all(users)
    db_session.commit()

    # Create book-user associations with different update times
    times = [
        now - timedelta(days=40),  # Inactive
        now - timedelta(days=5),   # Active
        now - timedelta(days=1)    # Active
    ]
    
    for user, update_time in zip(users, times):
        book_user = BookUser(
            work_id=sample_book.work_id,
            user_id=user.id,
            status="reading"
        )
        book_user.updated_at = update_time
        db_session.add(book_user)
    db_session.commit()

    active_users = user_repo.get_active_readers(days=30)
    assert len(active_users) == 2

def test_get_user_with_books(user_repo, db_session, sample_user):
    """Test retrieving a user with their book relationships."""
    # Create multiple books
    books = [
        Book(goodreads_id=f"book_{i}", work_id=f"work_{i}", title=f"Book {i}")
        for i in range(2)
    ]
    db_session.add_all(books)
    db_session.commit()

    # Create book-user associations
    for book in books:
        book_user = BookUser(
            work_id=book.work_id,
            user_id=sample_user.id,
            status="reading"
        )
        db_session.add(book_user)
    db_session.commit()

    user = user_repo.get_user_with_books(sample_user.id)
    assert user is not None
    assert len(user.book_users) == 2
    assert all(isinstance(bu.book, Book) for bu in user.book_users)

def test_update_book_status(user_repo, db_session, sample_user, sample_book):
    """Test updating a user's book status."""
    # Create a library entry for the book
    library_entry = Library(
        title=sample_book.title,
        work_id=sample_book.work_id,
        goodreads_id=sample_book.goodreads_id
    )
    db_session.add(library_entry)
    db_session.commit()

    # Initial status update
    book_user = user_repo.update_book_status(
        user_id=sample_user.id,
        goodreads_id=sample_book.goodreads_id,
        status="reading",
        source="test",
        started_at=datetime.now(UTC)
    )
    assert book_user is not None
    assert book_user.status == "reading"

    # Update existing status
    updated = user_repo.update_book_status(
        user_id=sample_user.id,
        goodreads_id=sample_book.goodreads_id,
        status="completed",
        finished_at=datetime.now(UTC)
    )
    assert updated is not None
    assert updated.status == "completed"
    assert updated.finished_at is not None

def test_update_book_status_nonexistent_book(user_repo, sample_user):
    """Test updating status for non-existent book."""
    result = user_repo.update_book_status(
        user_id=sample_user.id,
        goodreads_id="nonexistent",
        status="reading"
    )
    assert result is None

def test_delete_book_status(user_repo, db_session, sample_user, sample_book):
    """Test deleting a book status."""
    # Create book-user relationship
    book_user = BookUser(
        work_id=sample_book.work_id,
        user_id=sample_user.id,
        status="reading"
    )
    db_session.add(book_user)
    db_session.commit()

    # Delete the status
    success = user_repo.delete_book_status(sample_user.id, sample_book.work_id)
    assert success is True

    # Verify it's deleted
    result = db_session.query(BookUser).filter_by(
        work_id=sample_book.work_id,
        user_id=sample_user.id
    ).first()
    assert result is None

def test_delete_nonexistent_book_status(user_repo):
    """Test deleting a non-existent book status."""
    success = user_repo.delete_book_status(999, "nonexistent_work_id")
    assert success is False

def test_get_user_stats(user_repo, db_session, sample_user, sample_book):
    """Test getting user reading statistics."""
    # Create book-user relationships with different statuses
    now = datetime.now(UTC)
    book_users = [
        BookUser(
            work_id=sample_book.work_id,
            user_id=sample_user.id,
            status="completed",
            started_at=now - timedelta(days=30),
            finished_at=now
        ),
        BookUser(
            work_id="work_2",
            user_id=sample_user.id,
            status="reading",
            started_at=now
        ),
        BookUser(
            work_id="work_3",
            user_id=sample_user.id,
            status="want_to_read"
        )
    ]
    
    # Create additional books
    books = [
        Book(
            goodreads_id="book_2",
            work_id="work_2",
            title="Test Book 2",
            pages=200
        ),
        Book(
            goodreads_id="book_3",
            work_id="work_3",
            title="Test Book 3",
            pages=300
        )
    ]
    
    db_session.add_all(books)
    db_session.add_all(book_users)
    db_session.commit()

    stats = user_repo.get_user_stats(sample_user.id)
    assert stats is not None
    assert stats["total_books"] == 3
    assert stats["currently_reading"] == 1
    assert stats["want_to_read"] == 1
    assert stats["books_read_this_year"] == 1 