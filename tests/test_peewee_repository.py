# tests/test_peewee_repository.py
from core.database.peewee_repositories.book_repository import BookRepository

def test_book_repository():
    repo = BookRepository()
    
    # Test get by ID
    book = repo.get_by_id("2767052")
    print(f"\nGet by ID:")
    print(f" - Found: {book.title if book else 'Not found'}")
    
    # Test search
    books = repo.search_books("hunger")
    print(f"\nSearch results:")
    for book in books:
        print(f" - {book.title}")
    
    # Test relationships
    book_with_rels = repo.get_with_relationships("2767052")
    if book_with_rels:
        print(f"\nBook with relationships:")
        print(f"Title: {book_with_rels.title}")
        
        # Access relationships
        print(f"Authors: {', '.join(author.name for author in book_with_rels.authors)}")
        print(f"Series: {', '.join(series.title for series in book_with_rels.series)}")
        print(f"Genres: {', '.join(genre.name for genre in book_with_rels.genres)}")

if __name__ == "__main__":
    test_book_repository()