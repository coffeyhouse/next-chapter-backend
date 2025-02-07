# tests/test_peewee.py
from core.database.peewee_models import db, Book

def test_connection():
    try:
        db.connect()
        print("✓ Connected to database")
        
        # Try reading a book
        book = Book.get_or_none(Book.goodreads_id == "2767052")
        print(f"✓ Read book: {book.title if book else 'Not found'}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_connection()