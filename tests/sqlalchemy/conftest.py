# tests/sqlalchemy/conftest.py
import os
import sys
import pytest
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlalchemy.orm import Session
from core.sqlalchemy.models import Base
from core.sqlalchemy.database import Database

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