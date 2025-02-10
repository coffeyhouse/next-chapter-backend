# core/sa/database.py
from contextlib import contextmanager
from typing import Iterator, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from core.sa.models import Base

class Database:
    def __init__(self, db_path: str = "books.db"):
        """Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},  # Allow SQLite to be used across threads
            poolclass=StaticPool
        )
        
        # Create sessionmaker
        self._SessionFactory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
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
        Base.metadata.create_all(self.engine)

    def create_db_and_tables(self):
        Base.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        return self._SessionFactory()


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

# Create a database instance
db = Database()

# Dependency for FastAPI
def get_db():
    """Get a database session.
    
    This is a FastAPI dependency that will be used to get a database session
    for each request. The session will be automatically closed when the request
    is complete.
    
    Yields:
        Session: A SQLAlchemy session
    """
    session = db.get_session()
    try:
        yield session
    finally:
        session.close()