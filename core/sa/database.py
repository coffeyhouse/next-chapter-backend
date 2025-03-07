# core/sa/database.py
from contextlib import contextmanager
from typing import Iterator, Optional, Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool, QueuePool
import os

from core.sa.models import Base

class Database:
    def __init__(self, connection_string: Optional[str] = None, **engine_kwargs):
        """Initialize database connection
        
        Args:
            connection_string: Database connection string (e.g., "postgresql://user:pass@localhost/books")
                              If None, will use the DATABASE_URL environment variable or fall back to SQLite
            engine_kwargs: Additional keyword arguments to pass to create_engine
        """
        self.connection_string = connection_string or os.getenv("DATABASE_URL", "sqlite:///books.db")
        self.is_sqlite = self.connection_string.startswith("sqlite")
        
        # SQLite-specific settings
        if self.is_sqlite:
            engine_kwargs.setdefault("connect_args", {"check_same_thread": False})
            engine_kwargs.setdefault("poolclass", NullPool)  # SQLite typically doesn't need connection pooling
            
        # PostgreSQL recommended settings
        else:
            engine_kwargs.setdefault("pool_size", 5)
            engine_kwargs.setdefault("max_overflow", 10)
            engine_kwargs.setdefault("poolclass", QueuePool)
            
        self.engine = create_engine(
            self.connection_string,
            **engine_kwargs
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