from pathlib import Path
import sqlite3

def init_db(db_path: str = "books.db"):
    """Initialize SQLite database with required schema"""
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Create tables
        conn.executescript("""
            -- Books table (main entity)
            CREATE TABLE IF NOT EXISTS book (
                goodreads_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                published_date TEXT,
                published_state TEXT,
                language TEXT,
                calibre_id INTEGER,
                pages INTEGER,
                isbn TEXT,
                goodreads_rating REAL,
                goodreads_votes INTEGER,
                description TEXT,
                image_url TEXT,
                similar_books_id TEXT,
                source TEXT,
                hidden BOOLEAN DEFAULT FALSE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_synced_at TEXT
            );
            
            -- Library table (unique concept)
            CREATE TABLE IF NOT EXISTS library (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                calibre_id INTEGER,
                goodreads_id TEXT UNIQUE,
                isbn TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_synced_at TEXT,
                FOREIGN KEY (goodreads_id) REFERENCES book(goodreads_id)
            );
            
            -- Series table (main entity)
            CREATE TABLE IF NOT EXISTS series (
                goodreads_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_synced_at TEXT
            );
            
            -- Book-Series relationship
            CREATE TABLE IF NOT EXISTS book_series (
                book_id TEXT,
                series_id TEXT,
                series_order REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (book_id, series_id),
                FOREIGN KEY (book_id) REFERENCES book(goodreads_id),
                FOREIGN KEY (series_id) REFERENCES series(goodreads_id)
            );
            
            -- Authors table (main entity)
            CREATE TABLE IF NOT EXISTS author (
                goodreads_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                bio TEXT,
                image_url TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_synced_at TEXT
            );
            
            -- Book-Author relationship
            CREATE TABLE IF NOT EXISTS book_author (
                book_id TEXT,
                author_id TEXT,
                role TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (book_id, author_id),
                FOREIGN KEY (book_id) REFERENCES book(goodreads_id),
                FOREIGN KEY (author_id) REFERENCES author(goodreads_id)
            );
            
            -- Genres table (main entity)
            CREATE TABLE IF NOT EXISTS genre (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            
            -- Book-Genre relationship
            CREATE TABLE IF NOT EXISTS book_genre (
                book_id TEXT,
                genre_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (book_id, genre_id),
                FOREIGN KEY (book_id) REFERENCES book(goodreads_id),
                FOREIGN KEY (genre_id) REFERENCES genre(id)
            );
            
            -- Awards table (main entity)
            CREATE TABLE IF NOT EXISTS award (
                goodreads_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            
            -- Book-Award relationship
            CREATE TABLE IF NOT EXISTS book_award (
                book_id TEXT,
                award_id TEXT,
                category TEXT,
                year INTEGER,
                designation TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (book_id, award_id),
                FOREIGN KEY (book_id) REFERENCES book(goodreads_id),
                FOREIGN KEY (award_id) REFERENCES award(goodreads_id)
            );
            
            -- Users table (main entity)
            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            
            -- Book-User relationship
            CREATE TABLE IF NOT EXISTS book_user (
                book_id TEXT,
                user_id INTEGER,
                status TEXT NOT NULL,
                source TEXT,
                started_at TEXT,
                finished_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (book_id, user_id),
                FOREIGN KEY (book_id) REFERENCES book(goodreads_id),
                FOREIGN KEY (user_id) REFERENCES user(id)
            );
            
            -- Book-Similar relationship
            CREATE TABLE IF NOT EXISTS book_similar (
                book_id TEXT,
                similar_book_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (book_id, similar_book_id),
                FOREIGN KEY (book_id) REFERENCES book(goodreads_id),
                FOREIGN KEY (similar_book_id) REFERENCES book(goodreads_id)
            );
            
            -- Book-Edition relationship
            CREATE TABLE IF NOT EXISTS book_edition (
                book_id TEXT,
                edition_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (book_id, edition_id),
                FOREIGN KEY (book_id) REFERENCES book(goodreads_id),
                FOREIGN KEY (edition_id) REFERENCES book(goodreads_id)
            );
        """)
        
        # Create performance indexes
        conn.executescript("""
            CREATE INDEX IF NOT EXISTS idx_book_title ON book(title);
            CREATE INDEX IF NOT EXISTS idx_library_calibre_id ON library(calibre_id);
            CREATE INDEX IF NOT EXISTS idx_library_isbn ON library(isbn);
            CREATE INDEX IF NOT EXISTS idx_series_title ON series(title);
            CREATE INDEX IF NOT EXISTS idx_author_name ON author(name);
            CREATE INDEX IF NOT EXISTS idx_book_user_status ON book_user(status);
            CREATE INDEX IF NOT EXISTS idx_book_user_finished ON book_user(finished_at);
        """)

if __name__ == "__main__":
    init_db()