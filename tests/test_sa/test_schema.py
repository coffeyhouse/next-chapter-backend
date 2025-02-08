# tests/test_sa/test_schema.py
import pytest
from core.sa.models import Book, Author, Genre, Series
from tests.test_sa.utils import print_table_schema, print_sample_data, compare_model_to_db


def test_book_schema(db_session):
    """Test Book model matches database schema"""
    print("\nBook Schema:")
    print_table_schema(db_session, "book")
    print_sample_data(db_session, "book", limit=2)
    
    differences = compare_model_to_db(db_session, Book)
    assert not differences, f"Schema differences found: {differences}"

def test_author_schema(db_session):
    """Test Author model matches database schema"""
    print("\nAuthor Schema:")
    print_table_schema(db_session, "author")
    print_sample_data(db_session, "author", limit=2)
    
    differences = compare_model_to_db(db_session, Author)
    assert not differences, f"Schema differences found: {differences}"

def test_genre_schema(db_session):
    """Test Genre model matches database schema"""
    print("\nGenre Schema:")
    print_table_schema(db_session, "genre")
    print_sample_data(db_session, "genre", limit=2)
    
    differences = compare_model_to_db(db_session, Genre)
    assert not differences, f"Schema differences found: {differences}"

def test_series_schema(db_session):
    """Test Series model matches database schema"""
    print("\nSeries Schema:")
    print_table_schema(db_session, "series")
    print_sample_data(db_session, "series", limit=2)
    
    differences = compare_model_to_db(db_session, Series)
    assert not differences, f"Schema differences found: {differences}"