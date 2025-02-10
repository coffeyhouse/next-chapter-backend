import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from core.resolvers.book_creator import BookCreator
from core.sa.models import Book, Author, Genre, Series

@pytest.fixture
def mock_book_scraper():
    with patch('core.resolvers.book_creator.BookScraper') as mock:
        scraper_instance = Mock()
        mock.return_value = scraper_instance
        yield scraper_instance

@pytest.fixture
def book_creator(db_session, mock_book_scraper):
    return BookCreator(db_session)

@pytest.fixture
def sample_scraped_data():
    return {
        'goodreads_id': '12345',
        'title': 'Test Book',
        'work_id': 'w12345',
        'published_date': '2023-01-01',
        'language': 'English',
        'pages': 300,
        'isbn': '1234567890',
        'goodreads_rating': 4.5,
        'goodreads_votes': 1000,
        'description': 'A test book description',
        'image_url': 'http://example.com/image.jpg',
        'authors': [
            {
                'goodreads_id': 'a12345',
                'name': 'Test Author'
            }
        ],
        'genres': [
            {
                'name': 'Test Genre'
            }
        ],
        'series': [
            {
                'goodreads_id': 's12345',
                'title': 'Test Series'
            }
        ]
    }

def test_create_book_from_goodreads_new_book(book_creator, mock_book_scraper, sample_scraped_data, db_session):
    # Setup
    mock_book_scraper.scrape_book.return_value = sample_scraped_data
    
    # Execute
    book = book_creator.create_book_from_goodreads('12345')
    
    # Verify
    assert book is not None
    assert book.goodreads_id == '12345'
    assert book.title == 'Test Book'
    assert book.work_id == 'w12345'
    assert book.language == 'English'
    assert book.pages == 300
    assert book.isbn == '1234567890'
    assert book.goodreads_rating == 4.5
    assert book.goodreads_votes == 1000
    assert book.description == 'A test book description'
    assert book.image_url == 'http://example.com/image.jpg'
    
    # Verify relationships
    assert len(book.authors) == 1
    assert book.authors[0].goodreads_id == 'a12345'
    assert book.authors[0].name == 'Test Author'
    
    assert len(book.genres) == 1
    assert book.genres[0].name == 'Test Genre'
    
    assert len(book.series) == 1
    assert book.series[0].goodreads_id == 's12345'
    assert book.series[0].title == 'Test Series'
    
    # Verify persistence
    db_session.expire_all()
    book = db_session.query(Book).filter_by(goodreads_id='12345').first()
    assert book is not None
    assert len(book.authors) == 1
    assert len(book.genres) == 1
    assert len(book.series) == 1

def test_create_book_from_goodreads_existing_book(book_creator, mock_book_scraper, sample_scraped_data, db_session):
    # Create existing book
    existing_book = Book(
        goodreads_id='12345',
        title='Existing Book',
        work_id='w12345'
    )
    db_session.add(existing_book)
    db_session.commit()
    
    # Setup mock
    mock_book_scraper.scrape_book.return_value = sample_scraped_data
    
    # Execute
    result = book_creator.create_book_from_goodreads('12345')
    
    # Verify
    assert result is None
    book = db_session.query(Book).filter_by(goodreads_id='12345').first()
    assert book.title == 'Existing Book'  # Original book unchanged

def test_create_book_from_goodreads_scrape_failure(book_creator, mock_book_scraper):
    # Setup mock to simulate scraping failure
    mock_book_scraper.scrape_book.return_value = None
    
    # Execute
    result = book_creator.create_book_from_goodreads('12345')
    
    # Verify
    assert result is None

def test_create_book_with_existing_relationships(book_creator, mock_book_scraper, sample_scraped_data, db_session):
    # Create existing author
    existing_author = Author(goodreads_id='a12345', name='Existing Author')
    db_session.add(existing_author)
    
    # Create existing genre
    existing_genre = Genre(name='Test Genre')
    db_session.add(existing_genre)
    
    # Create existing series
    existing_series = Series(
        goodreads_id='s12345',
        title='Existing Series'
    )
    db_session.add(existing_series)
    
    db_session.commit()
    
    # Setup mock
    mock_book_scraper.scrape_book.return_value = sample_scraped_data
    
    # Execute
    book = book_creator.create_book_from_goodreads('12345')
    
    # Verify relationships reuse existing records
    assert book is not None
    assert len(book.authors) == 1
    assert book.authors[0] is existing_author
    assert book.authors[0].name == 'Existing Author'  # Name not updated
    
    assert len(book.genres) == 1
    assert book.genres[0] is existing_genre
    
    assert len(book.series) == 1
    assert book.series[0] is existing_series
    assert book.series[0].title == 'Existing Series'  # Changed from name to title 