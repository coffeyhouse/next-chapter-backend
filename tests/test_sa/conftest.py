# tests/test_sa/conftest.py
import os
import sys
import pytest
from pathlib import Path

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
    return Database(db_path="books.db")

@pytest.fixture(scope="function")
def db_session(database):
    """Create a new database session for a test"""
    session: Session = database._SessionFactory()
    try:
        yield session
    finally:
        session.close()