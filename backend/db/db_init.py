import sqlite3
from pathlib import Path

def init_db(db_path: str = "books.db"):
    """Initialize the SQLite database with all required tables"""
    
    # Create the database file if it doesn't exist
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    
    with sqlite3.connect(db_path) as conn:
        # Enable foreign key support
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Create tables
        conn.executescript("""
            -- Books table
            CREATE TABLE IF NOT EXISTS books (
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
            
            -- Library table
            CREATE TABLE IF NOT EXISTS library (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                calibre_id INTEGER,
                goodreads_id TEXT UNIQUE,
                isbn TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_synced_at TEXT,
                FOREIGN KEY (goodreads_id) REFERENCES books(goodreads_id)
            );
            
            -- Series table
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
                FOREIGN KEY (book_id) REFERENCES books(goodreads_id),
                FOREIGN KEY (series_id) REFERENCES series(goodreads_id)
            );
            
            -- Authors table
            CREATE TABLE IF NOT EXISTS authors (
                goodreads_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                bio TEXT,
                image_url TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_synced_at TEXT
            );
            
            -- Author-Book relationship
            CREATE TABLE IF NOT EXISTS author_books (
                book_id TEXT,
                author_id TEXT,
                role TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (book_id, author_id),
                FOREIGN KEY (book_id) REFERENCES books(goodreads_id),
                FOREIGN KEY (author_id) REFERENCES authors(goodreads_id)
            );
            
            -- Genres table
            CREATE TABLE IF NOT EXISTS genres (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            
            -- Book-Genre relationship
            CREATE TABLE IF NOT EXISTS book_genres (
                genre_id INTEGER,
                book_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (genre_id, book_id),
                FOREIGN KEY (genre_id) REFERENCES genres(id),
                FOREIGN KEY (book_id) REFERENCES books(goodreads_id)
            );
            
            -- Awards table
            CREATE TABLE IF NOT EXISTS awards (
                goodreads_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            
            -- Book-Award relationship
            CREATE TABLE IF NOT EXISTS book_awards (
                book_id TEXT,
                award_id TEXT,
                category TEXT,
                year INTEGER,
                designation TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (book_id, award_id),
                FOREIGN KEY (book_id) REFERENCES books(goodreads_id),
                FOREIGN KEY (award_id) REFERENCES awards(goodreads_id)
            );
            
            -- Users table
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            
            -- Book-User relationship (reading status)
            CREATE TABLE IF NOT EXISTS book_users (
                book_id TEXT,
                user_id INTEGER,
                status TEXT NOT NULL,
                source TEXT,
                started_at TEXT,
                finished_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (book_id, user_id),
                FOREIGN KEY (book_id) REFERENCES books(goodreads_id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            
            -- Similar Books relationship
            CREATE TABLE IF NOT EXISTS similar_books (
                book_id TEXT,
                similar_book_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (book_id, similar_book_id),
                FOREIGN KEY (book_id) REFERENCES books(goodreads_id),
                FOREIGN KEY (similar_book_id) REFERENCES books(goodreads_id)
            );
            
            -- Book Editions relationship
            CREATE TABLE IF NOT EXISTS book_editions (
                book_id TEXT,
                edition_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (book_id, edition_id),
                FOREIGN KEY (book_id) REFERENCES books(goodreads_id),
                FOREIGN KEY (edition_id) REFERENCES books(goodreads_id)
            );
        """)
        
        # Create indexes for performance
        conn.executescript("""
            CREATE INDEX IF NOT EXISTS idx_books_title ON books(title);
            CREATE INDEX IF NOT EXISTS idx_library_calibre_id ON library(calibre_id);
            CREATE INDEX IF NOT EXISTS idx_library_isbn ON library(isbn);
            CREATE INDEX IF NOT EXISTS idx_series_title ON series(title);
            CREATE INDEX IF NOT EXISTS idx_authors_name ON authors(name);
            CREATE INDEX IF NOT EXISTS idx_book_users_status ON book_users(status);
            CREATE INDEX IF NOT EXISTS idx_book_users_finished ON book_users(finished_at);
        """)

if __name__ == "__main__":
    init_db()