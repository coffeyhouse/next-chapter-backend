import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.sa.database import Database
from core.sa.repositories.author import AuthorRepository
from core.sa.repositories.book import BookRepository
from core.sa.repositories.genre import GenreRepository
from core.sa.repositories.series import SeriesRepository
from sqlalchemy import text, inspect

def main():
    # Connect to your real database
    db_path = "books.db"
    print(f"\nTrying to connect to database at: {os.path.abspath(db_path)}")
    db = Database(db_path)
    
    try:
        # List all tables in the database
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        print("\nExisting tables in database:", existing_tables)
        
        # For each table, show its columns
        for table in existing_tables:
            columns = inspector.get_columns(table)
            print(f"\nColumns in {table}:")
            for col in columns:
                print(f"- {col['name']} ({col['type']})")
        
        # Initialize repositories
        author_repo = AuthorRepository(db.session)
        book_repo = BookRepository(db.session)
        genre_repo = GenreRepository(db.session)
        series_repo = SeriesRepository(db.session)
        
        # Check if tables exist and have data
        print("\nChecking table counts:")
        for table in existing_tables:
            result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"- {table}: {result} records")
            
        # Example queries - uncomment and modify as needed
        
        # Search authors
        print("\nSearching authors:")
        authors = author_repo.search_authors("")  # Empty query to get all authors
        print(f"Found {len(authors)} authors")
        for author in authors[:5]:  # Show first 5
            print(f"- {author.name} (ID: {author.goodreads_id})")
        
        # Search books
        print("\nSearching books:")
        books = book_repo.search_books("")  # Empty query to get all books
        print(f"Found {len(books)} books")
        for book in books[:5]:  # Show first 5
            print(f"- {book.title} (ID: {book.goodreads_id})")
            
        # Get genres
        print("\nListing genres:")
        genres = genre_repo.search_genres("")  # Empty query to get all genres
        print(f"Found {len(genres)} genres")
        for genre in genres[:5]:  # Show first 5
            print(f"- {genre.name}")
            
        # Get series
        print("\nListing series:")
        series_list = series_repo.search_series("")  # Empty query to get all series
        print(f"Found {len(series_list)} series")
        for series in series_list[:5]:  # Show first 5
            print(f"- {series.title} (ID: {series.goodreads_id})")
            
        # Example of more specific queries
        print("\nExample specific queries:")
        
        # Get books by rating
        highly_rated = book_repo.get_books_with_rating_above(4.5)
        print(f"Found {len(highly_rated)} books rated above 4.5")
        
        # Get recent books
        recent_books = book_repo.get_recent_books(limit=5)
        print("\nRecent books:")
        for book in recent_books:
            print(f"- {book.title}")
            
        # Get prolific authors
        prolific = author_repo.get_prolific_authors(min_books=10)
        print(f"\nFound {len(prolific)} authors with 10+ books")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close_session()

if __name__ == "__main__":
    main() 