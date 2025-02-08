# core/sqlalchemy/database.py
from contextlib import contextmanager
from typing import Iterator, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

class Database:
    def __init__(self, db_path: str = "books.db"):
        """Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        db_url = f"sqlite:///{db_path}"
        
        # Create engine with SQLite-specific configurations
        self.engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},  # Allow SQLite to be used across threads
            echo=False  # Set to True to see SQL queries
        )
        
        # Create sessionmaker
        self._SessionFactory = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False
        )
        
        # Store for thread-local session
        self._session: Optional[Session] = None

    @property
    def session(self) -> Session:
        """Get the current session or create a new one"""
        if self._session is None:
            self._session = self._SessionFactory()
        return self._session

    def close_session(self) -> None:
        """Close the current session if it exists"""
        if self._session is not None:
            self._session.close()
            self._session = None

    @contextmanager
    def get_db(self) -> Iterator[Session]:
        """Context manager for database sessions"""
        session: Session = self._SessionFactory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            
    def init_db(self) -> None:
        """Initialize database schema"""
        from .models import Base
        Base.metadata.create_all(bind=self.engine)


# Usage example:
if __name__ == "__main__":
    # Create database instance
    db = Database()
    
    # Initialize schema
    db.init_db()
    
    # Example using context manager
    with db.get_db() as session:
        # Perform database operations
        pass