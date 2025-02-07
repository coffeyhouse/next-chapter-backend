# tests/test_book_repository.py
from datetime import datetime, timedelta
from core.database.peewee_repositories.book_repository import BookRepository
from core.database.peewee_models import Book, Genre, BookUser

def test_basic_operations():
    print("\nTesting basic operations...")
    repo = BookRepository()
    
    # Test get by ID
    book = repo.get_by_id("2767052")
    assert book is not None
    assert book.title == "The Hunger Games"
    print(f" - Get by ID: Found '{book.title}'")
    
    # Test search
    books = repo.search_books("hunger")
    assert len(books) > 0
    assert any("Hunger" in book.title for book in books)
    print(f" - Search results: Found {len(books)} books")
    for book in books[:3]:  # Show first 3 results
        print(f"   * {book.title}")

def test_relationships():
    print("\nTesting relationships...")
    repo = BookRepository()
    book = repo.get_with_relationships("2767052")
    
    assert book is not None
    # Author tests
    assert len(book.authors) > 0
    print(f" - Authors: {', '.join(a.name for a in book.authors)}")
    
    # Series tests
    assert len(book.series) > 0
    print(f" - Series: {', '.join(s.title for s in book.series)}")
    
    # Genre tests
    assert len(book.genres) > 0
    print(f" - Genres: {', '.join(g.name for g in book.genres)}")

def test_genre_filtering():
    print("\nTesting genre filtering...")
    repo = BookRepository()
    
    # Test getting books by genre
    books = repo.get_books_by_genre("Fiction")
    print(f" - Found {len(books)} books in Fiction genre")
    print(" - Top 3 books by votes:")
    for book in books[:3]:
        print(f"   * {book.title} ({book.goodreads_votes or 0} votes)")

def test_library_books():
    print("\nTesting library books...")
    repo = BookRepository()
    
    # Test getting library books
    library_books = repo.get_library_books()
    print(f" - Found {len(library_books)} books in library")
    print(" - First 3 books:")
    for book in library_books[:3]:
        print(f"   * {book.title}")

def test_unsynced_books():
    print("\nTesting unsynced books...")
    repo = BookRepository()
    
    # Test getting unsynced books
    cutoff_days = 30
    unsynced = repo.get_unsynced_books(days=cutoff_days)
    print(f" - Found {len(unsynced)} books not synced in {cutoff_days} days")
    print(" - First 3 unsynced books:")
    for book in unsynced[:3]:
        print(f"   * {book.title} (Last synced: {book.last_synced_at or 'Never'})")

def test_update_operations():
    print("\nTesting update operations...")
    repo = BookRepository()
    
    # Test updating book details
    test_book_id = "2767052"
    update_data = {
        'goodreads_rating': 4.5,
        'goodreads_votes': 1000000
    }
    
    updated_book = repo.update_book(test_book_id, update_data)
    print(f" - Updated '{updated_book.title}':")
    print(f"   * New rating: {updated_book.goodreads_rating}")
    print(f"   * New votes: {updated_book.goodreads_votes}")
    
    # Restore original data
    original_data = {
        'goodreads_rating': 4.34,
        'goodreads_votes': 6976884
    }
    repo.update_book(test_book_id, original_data)
    print(" - Restored original data")

def test_user_operations():
    print("\nTesting user operations...")
    repo = BookRepository()
    test_book = repo.get_by_id("2767052")
    test_user_id = 1
    
    # Test updating reading status
    success = repo.update_reading_status(
        test_book.work_id,
        test_user_id,
        "reading"
    )
    print(f" - Updated reading status for '{test_book.title}'")
    print(f"   * Status set to: reading")
    print(f"   * Success: {success}")

    # Clean up
    BookUser.delete().where(
        (BookUser.work_id == test_book.work_id) & 
        (BookUser.user_id == test_user_id)
    ).execute()
    print(" - Cleaned up test data")

def test_upsert_book():
    print("\nTesting upsert operations...")
    repo = BookRepository()
    
    # Test inserting new book
    new_book_data = {
        'goodreads_id': 'test123',
        'work_id': 'work123',
        'title': 'Test Book',
        'source': 'test'
    }
    
    book = repo.upsert_book(new_book_data)
    print(f" - Inserted new book: '{book.title}'")
    
    # Test updating existing book
    update_data = {
        'goodreads_id': 'test123',
        'work_id': 'work123',
        'title': 'Updated Test Book',
        'source': 'test'
    }
    
    updated_book = repo.upsert_book(update_data)
    print(f" - Updated book title to: '{updated_book.title}'")
    
    # Clean up test data
    Book.delete().where(Book.goodreads_id == 'test123').execute()
    print(" - Cleaned up test data")

if __name__ == "__main__":
    print("Running Book Repository Tests...")
    print("=" * 50)
    
    # Run all tests
    test_basic_operations()
    test_relationships()
    test_genre_filtering()
    test_library_books()
    test_unsynced_books()
    test_update_operations()
    test_user_operations()
    test_upsert_book()
    
    print("\n" + "=" * 50)
    print("All tests passed successfully!")