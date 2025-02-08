# tests/test_sa/conftest.py
import os
import sys
import pytest
from pathlib import Path
from sqlalchemy.sql import text

# Add debugging information
print("\nCurrent working directory:", os.getcwd())
print("__file__:", __file__)

# Calculate project root
project_root = str(Path(__file__).parent.parent.parent)
print("Project root path:", project_root)
print("Current sys.path:", sys.path)

# Add project root to Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    print("Updated sys.path:", sys.path)

try:
    from sqlalchemy.orm import Session
    print("Successfully imported sqlalchemy.orm")
except ImportError as e:
    print("Failed to import sqlalchemy.orm:", str(e))
    
try:
    from core.sa.models import Base
    print("Successfully imported core.sa.models")
except ImportError as e:
    print("Failed to import core.sa.models:", str(e))
    
try:
    from core.sa.database import Database
    print("Successfully imported core.sa.database")
except ImportError as e:
    print("Failed to import core.sa.database:", str(e))

@pytest.fixture(scope="session")
def database():
    """Create a test database instance"""
    db = Database(db_path="books.db")
    
    # Drop all tables and recreate schema
    Base.metadata.drop_all(db.engine)
    Base.metadata.create_all(db.engine)
    
    return db

@pytest.fixture(autouse=True)
def cleanup_db(db_session):
    """Clean up database tables before each test"""
    # Delete all data from tables in reverse order of dependencies
    db_session.execute(text("DELETE FROM book_series"))
    db_session.execute(text("DELETE FROM book_genre"))
    db_session.execute(text("DELETE FROM book_author"))
    db_session.execute(text("DELETE FROM series"))
    db_session.execute(text("DELETE FROM book"))
    db_session.execute(text("DELETE FROM author"))
    db_session.execute(text("DELETE FROM genre"))
    db_session.commit()
    yield
    # Clean up after test as well
    db_session.rollback()

@pytest.fixture(scope="function")
def db_session(database):
    """Create a new database session for a test"""
    session: Session = database._SessionFactory()
    try:
        yield session
    finally:
        session.close()