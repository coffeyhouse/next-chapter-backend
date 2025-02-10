# tests/test_sa/test_repositories/test_library_repository.py

import pytest
from datetime import datetime, UTC
from core.sa.repositories.library import LibraryRepository
from core.sa.models import Library, Book

@pytest.fixture
def library_repo(db_session):
    """Fixture to create a LibraryRepository instance."""
    return LibraryRepository(db_session)

@pytest.fixture
def sample_library(db_session, sample_book):
    """Fixture to create and return a sample Library object."""
    library = Library(
        title="Test Library Entry",
        work_id=sample_book.work_id,
        calibre_id=1,
        goodreads_id="lib_1",
        isbn="1234567890"
    )
    db_session.add(library)
    db_session.commit()
    return library

@pytest.fixture
def multiple_library_entries(db_session, multiple_books):
    """Fixture to create multiple library entries."""
    entries = []
    for i, book in enumerate(multiple_books[:5]):  # Create 5 entries
        library = Library(
            title=f"Library Entry {i}",
            work_id=book.work_id,
            calibre_id=i + 1,
            goodreads_id=f"lib_{i}",
            isbn=f"ISBN{i}"
        )
        db_session.add(library)
        entries.append(library)
    db_session.commit()
    return entries

def test_get_by_id(library_repo, sample_library):
    """Test fetching a library entry by its ID."""
    fetched = library_repo.get_by_id(sample_library.id)
    assert fetched is not None
    assert fetched.id == sample_library.id
    assert fetched.title == "Test Library Entry"

def test_get_by_nonexistent_id(library_repo):
    """Test fetching a library entry with non-existent ID."""
    result = library_repo.get_by_id(999)
    assert result is None

def test_get_by_calibre_id(library_repo, sample_library):
    """Test fetching a library entry by Calibre ID."""
    fetched = library_repo.get_by_calibre_id(sample_library.calibre_id)
    assert fetched is not None
    assert fetched.calibre_id == sample_library.calibre_id

def test_get_by_goodreads_id(library_repo, sample_library):
    """Test fetching a library entry by Goodreads ID."""
    fetched = library_repo.get_by_goodreads_id(sample_library.goodreads_id)
    assert fetched is not None
    assert fetched.goodreads_id == sample_library.goodreads_id

def test_get_by_isbn(library_repo, sample_library):
    """Test fetching library entries by ISBN."""
    results = library_repo.get_by_isbn(sample_library.isbn)
    assert len(results) == 1
    assert results[0].isbn == sample_library.isbn

def test_search_by_title(library_repo, multiple_library_entries):
    """Test searching for library entries by title."""
    results = library_repo.search_by_title("Library Entry")
    assert len(results) == 5
    assert all("Library Entry" in entry.title for entry in results)

def test_search_by_title_with_limit(library_repo, multiple_library_entries):
    """Test search respects the limit parameter."""
    results = library_repo.search_by_title("Library Entry", limit=3)
    assert len(results) == 3

def test_get_library_with_book(library_repo, sample_library, sample_book):
    """Test retrieving a library entry with its book relationship."""
    library = library_repo.get_library_with_book(sample_library.id)
    assert library is not None
    assert library.book is not None
    assert library.book.work_id == sample_book.work_id

def test_get_all_by_work_id(library_repo, sample_library):
    """Test retrieving all library entries for a work ID."""
    results = library_repo.get_all_by_work_id(sample_library.work_id)
    assert len(results) == 1
    assert results[0].work_id == sample_library.work_id

def test_create_entry(library_repo, sample_book):
    """Test creating a new library entry."""
    library = library_repo.create_entry(
        title="New Library Entry",
        work_id=sample_book.work_id,
        calibre_id=100,
        goodreads_id="new_lib",
        isbn="0987654321"
    )
    assert library is not None
    assert library.title == "New Library Entry"
    assert library.work_id == sample_book.work_id
    assert library.calibre_id == 100
    assert library.goodreads_id == "new_lib"
    assert library.isbn == "0987654321"

def test_create_entry_minimal(library_repo, sample_book):
    """Test creating a library entry with minimal information."""
    library = library_repo.create_entry(
        title="Minimal Entry",
        work_id=sample_book.work_id
    )
    assert library is not None
    assert library.title == "Minimal Entry"
    assert library.work_id == sample_book.work_id
    assert library.calibre_id is None
    assert library.goodreads_id is None
    assert library.isbn is None

def test_update_entry(library_repo, sample_library):
    """Test updating an existing library entry."""
    updated = library_repo.update_entry(
        library_id=sample_library.id,
        title="Updated Title",
        calibre_id=200,
        goodreads_id="updated_lib",
        isbn="5555555555"
    )
    assert updated is not None
    assert updated.title == "Updated Title"
    assert updated.calibre_id == 200
    assert updated.goodreads_id == "updated_lib"
    assert updated.isbn == "5555555555"

def test_update_entry_partial(library_repo, sample_library):
    """Test partially updating a library entry."""
    original_calibre_id = sample_library.calibre_id
    updated = library_repo.update_entry(
        library_id=sample_library.id,
        title="New Title"
    )
    assert updated is not None
    assert updated.title == "New Title"
    assert updated.calibre_id == original_calibre_id  # Should remain unchanged

def test_update_nonexistent_entry(library_repo):
    """Test updating a non-existent library entry."""
    result = library_repo.update_entry(
        library_id=999,
        title="New Title"
    )
    assert result is None

def test_delete_entry(library_repo, sample_library):
    """Test deleting a library entry."""
    success = library_repo.delete_entry(sample_library.id)
    assert success is True
    assert library_repo.get_by_id(sample_library.id) is None

def test_delete_nonexistent_entry(library_repo):
    """Test deleting a non-existent library entry."""
    success = library_repo.delete_entry(999)
    assert success is False 