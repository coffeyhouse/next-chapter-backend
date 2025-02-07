# tests/test_peewee_models.py
from core.database.peewee_models import *

def test_relationships():
    try:
        db.connect()
        
        # Get a book with its relationships
        book = (Book
               .select()
               .join(BookAuthor)
               .join(Author)
               .where(Book.goodreads_id == "2767052")
               .first())
        
        if book:
            print(f"\nFound book: {book.title}")
            
            # Get authors
            authors = (Author
                     .select()
                     .join(BookAuthor)
                     .where(BookAuthor.work_id == book.work_id))
            
            print("\nAuthors:")
            for author in authors:
                print(f" - {author.name}")
            
            # Get series
            series = (Series
                     .select()
                     .join(BookSeries)
                     .where(BookSeries.work_id == book.work_id))
            
            print("\nSeries:")
            for s in series:
                print(f" - {s.title}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_relationships()