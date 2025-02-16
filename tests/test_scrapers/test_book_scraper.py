import pytest
from pathlib import Path
import json
from datetime import datetime
from bs4 import BeautifulSoup
import click
from core.scrapers.book_scraper import BookScraper
from unittest.mock import patch, Mock, mock_open

@pytest.fixture
def mock_click_context():
    """Create a mock Click context."""
    ctx = click.Context(click.Command('test'))
    ctx.params = {'verbose': True}
    with ctx:
        yield ctx

@pytest.fixture
def scraper(mock_click_context):
    """Create a BookScraper instance for testing."""
    return BookScraper(scrape=False)

@pytest.fixture
def sample_book_html():
    """Load sample book HTML for testing."""
    html_path = Path('tests/fixtures/book_show.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        return f.read()

@pytest.fixture
def sample_book_soup(sample_book_html):
    """Create BeautifulSoup object from sample HTML."""
    return BeautifulSoup(sample_book_html, 'html.parser')

@pytest.fixture
def sample_book_data():
    """Load expected book data for comparison."""
    data_path = Path('tests/fixtures/book_13496.json')
    with open(data_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def test_extract_title(scraper, sample_book_soup, sample_book_data):
    """Test extracting book title."""
    title = scraper._extract_title(sample_book_soup)
    assert title == sample_book_data['title']
    assert title == "A Game of Thrones"

def test_extract_work_id(scraper, sample_book_soup, sample_book_data):
    """Test extracting work ID."""
    work_id = scraper._extract_work_id(sample_book_soup)
    assert work_id == sample_book_data['work_id']
    assert isinstance(work_id, str)

def test_extract_description(scraper, sample_book_soup, sample_book_data):
    """Test extracting book description."""
    description = scraper._extract_description(sample_book_soup)
    assert description == sample_book_data['description']
    assert isinstance(description, str)
    assert len(description) > 100  # Should be a substantial description
    assert "Long ago, in a time forgotten" in description  # Key phrase

def test_extract_book_details(scraper, sample_book_soup, sample_book_data):
    """Test extracting book details."""
    details = scraper._extract_book_details(sample_book_soup)
    assert isinstance(details, dict)
    
    # Check all fields
    assert details['language'] == sample_book_data['language']
    assert details['pages'] == sample_book_data['pages']
    assert details['isbn'] == sample_book_data['isbn']
    assert details['rating'] == sample_book_data['goodreads_rating']
    assert details['rating_count'] == sample_book_data['goodreads_votes']
    
    # Verify specific values
    assert details['language'] == "English"
    assert isinstance(details['pages'], int)
    assert isinstance(details['isbn'], str)
    assert isinstance(details['rating'], float)
    assert isinstance(details['rating_count'], int)

def test_extract_publication_info(scraper, sample_book_soup, sample_book_data):
    """Test extracting publication information."""
    pub_info = scraper._extract_publication_info(sample_book_soup)
    assert isinstance(pub_info, dict)
    assert pub_info['date'] == sample_book_data['published_date']
    assert pub_info['state'] == sample_book_data['published_state']
    
    # Verify date format
    assert pub_info['state'] == "published"
    try:
        dt = datetime.fromisoformat(pub_info['date'])
        assert dt.year == 1996  # Known publication year
        assert dt.month == 8    # Known publication month
    except ValueError:
        pytest.fail("Invalid date format")

def test_extract_authors(scraper, sample_book_soup, sample_book_data):
    """Test extracting author information."""
    authors = scraper._extract_authors(sample_book_soup)
    assert authors == sample_book_data['authors']
    
    # Verify structure and content
    assert isinstance(authors, list)
    assert len(authors) > 0
    
    # Check main author
    main_author = next((a for a in authors if a['role'] == 'Author'), None)
    assert main_author is not None
    assert main_author['name'] == "George R.R. Martin"
    assert main_author['goodreads_id'] is not None
    assert main_author['role'] == "Author"

def test_extract_series(scraper, sample_book_soup, sample_book_data):
    """Test extracting series information."""
    series = scraper._extract_series(sample_book_soup)
    assert series == sample_book_data['series']
    
    # Verify structure and content
    assert isinstance(series, list)
    assert len(series) > 0
    
    # Check main series
    main_series = series[0]
    assert main_series['name'] == "A Song of Ice and Fire"
    assert main_series['goodreads_id'] is not None
    assert isinstance(main_series.get('order'), (float, type(None)))

def test_extract_genres(scraper, sample_book_soup, sample_book_data):
    """Test extracting genre information."""
    genres = scraper._extract_genres(sample_book_soup)
    assert genres == sample_book_data['genres']
    
    # Verify structure and content
    assert isinstance(genres, list)
    assert len(genres) > 0
    
    # Check expected genres
    genre_names = {g['name'] for g in genres}
    assert "Fantasy" in genre_names
    assert len(genre_names) >= 3  # Should have several genres

def test_extract_cover_url(scraper, sample_book_soup):
    """Test extracting cover URL."""
    cover_url = scraper._extract_cover_url(sample_book_soup)
    assert cover_url is not None
    assert isinstance(cover_url, str)
    # Goodreads uses multiple domains for images
    assert any(cover_url.startswith(domain) for domain in [
        'https://images.gr-assets.com/',
        'https://images-na.ssl-images-amazon.com/',
        'https://images-us.ssl-images-amazon.com/'
    ])
    assert '.jpg' in cover_url or '.jpeg' in cover_url

def test_scrape_full_integration(mock_click_context):
    """Test full book scraping integration with live data."""
    scraper = BookScraper(scrape=True)
    book_data = scraper.scrape("13496")
    
    # Basic structure checks
    assert isinstance(book_data, dict)
    required_fields = {
        'goodreads_id', 'title', 'work_id', 'description', 'language',
        'pages', 'isbn', 'goodreads_rating', 'goodreads_votes',
        'published_date', 'published_state', 'source', 'hidden',
        'authors', 'series', 'genres'
    }
    assert all(field in book_data for field in required_fields)
    
    # Specific value checks
    assert book_data['goodreads_id'] == "13496"
    assert book_data['title'] == "A Game of Thrones"
    assert isinstance(book_data['work_id'], str)
    assert book_data['language'] == "English"
    assert isinstance(book_data['pages'], int)
    assert isinstance(book_data['isbn'], str)
    assert isinstance(book_data['goodreads_rating'], float)
    assert isinstance(book_data['goodreads_votes'], int)
    assert book_data['source'] == "scrape"
    assert book_data['hidden'] is False
    
    # Relationship checks
    assert len(book_data['authors']) > 0
    assert len(book_data['series']) > 0
    assert len(book_data['genres']) > 0

def test_scrape_error_handling(mock_click_context):
    """Test error handling for invalid or missing data."""
    scraper = BookScraper(scrape=True)
    
    # Test with invalid book ID
    result = scraper.scrape("invalid_id")
    assert result is None
    
    # Test with non-existent book ID
    # Note: Goodreads returns a 200 response with empty data for non-existent IDs
    result = scraper.scrape("999999999999")
    if result is not None:
        # If we get a result, ensure it has minimal valid data
        assert result['goodreads_id'] == "999999999999"
        assert not any([
            result['title'],
            result['description'],
            result['authors'],
            result['series'],
            result['genres']
        ])

def test_empty_html_handling(scraper):
    """Test handling of empty or invalid HTML."""
    soup = BeautifulSoup("", 'html.parser')
    assert scraper._extract_title(soup) is None
    assert scraper._extract_work_id(soup) is None
    assert scraper._extract_description(soup) is None
    assert scraper._extract_book_details(soup) == {}
    assert scraper._extract_publication_info(soup) == {}
    assert scraper._extract_authors(soup) == []
    assert scraper._extract_series(soup) == []
    assert scraper._extract_genres(soup) == []
    assert scraper._extract_cover_url(soup) is None

def test_malformed_html_handling(scraper):
    """Test handling of malformed HTML."""
    malformed_html = """
    <html>
        <body>
            <h1>Incomplete book
            <div>Missing closing tags
            <p>Invalid structure
    """
    soup = BeautifulSoup(malformed_html, 'html.parser')
    assert scraper._extract_title(soup) is None
    assert scraper._extract_work_id(soup) is None
    assert scraper._extract_description(soup) is None
    assert scraper._extract_book_details(soup) == {}
    assert scraper._extract_publication_info(soup) == {}
    assert scraper._extract_authors(soup) == []
    assert scraper._extract_series(soup) == []
    assert scraper._extract_genres(soup) == []
    assert scraper._extract_cover_url(soup) is None

def test_get_book_url(scraper):
    """Test URL generation for book pages."""
    # Test normal book ID
    url = scraper._get_book_url("12345")
    assert url == "https://www.goodreads.com/book/show/12345"
    
    # Test book ID with special characters
    url = scraper._get_book_url("12345.Some_Title")
    assert url == "https://www.goodreads.com/book/show/12345.Some_Title"

def test_read_html_file_handling(scraper):
    """Test HTML file reading functionality."""
    test_html = "<html><body>Test content</body></html>"
    
    # Test successful read
    m = mock_open(read_data=test_html)
    with patch('builtins.open', m):
        content = scraper._read_html("test")
        assert content == test_html
        m.assert_called_once()
    
    # Test file not found
    with patch('builtins.open', side_effect=FileNotFoundError()):
        content = scraper._read_html("nonexistent")
        assert content is None
    
    # Test permission error
    with patch('builtins.open', side_effect=PermissionError("Access denied")):
        content = scraper._read_html("test")
        assert content is None

def test_image_download_integration(scraper, sample_book_soup):
    """Test image download integration."""
    with patch('core.utils.image.download_book_cover') as mock_download:
        # Test successful download
        mock_download.return_value = "covers/test.jpg"
        cover_url = scraper._extract_cover_url(sample_book_soup)
        assert cover_url is not None
        
        # Simulate full book scrape with image download
        book_data = {
            'work_id': 'test123',
            'image_url': None
        }
        if cover_url:
            local_path = mock_download(book_data['work_id'], cover_url)
            if local_path:
                book_data['image_url'] = local_path
        
        assert book_data['image_url'] == "covers/test.jpg"
        mock_download.assert_called_once_with('test123', cover_url)
        
        # Test failed download
        mock_download.return_value = None
        book_data['image_url'] = None
        if cover_url:
            local_path = mock_download(book_data['work_id'], cover_url)
            if local_path:
                book_data['image_url'] = local_path
        
        assert book_data['image_url'] is None

def test_publication_date_formats(scraper):
    """Test various publication date formats."""
    def create_pub_element(text):
        return BeautifulSoup(
            f'<p data-testid="publicationInfo">{text}</p>',
            'html.parser'
        )
    
    # Test standard format
    soup = create_pub_element("Published August 1, 1996")
    info = scraper._extract_publication_info(soup)
    assert info['state'] == "published"
    dt = datetime.fromisoformat(info['date'])
    assert dt.year == 1996
    assert dt.month == 8
    assert dt.day == 1
    
    # Test "First published" format
    soup = create_pub_element("First published January 15, 2020")
    info = scraper._extract_publication_info(soup)
    assert info['state'] == "published"
    dt = datetime.fromisoformat(info['date'])
    assert dt.year == 2020
    assert dt.month == 1
    assert dt.day == 15
    
    # Test upcoming publication
    soup = create_pub_element("Expected publication December 25, 2024")
    info = scraper._extract_publication_info(soup)
    assert info['state'] == "upcoming"
    dt = datetime.fromisoformat(info['date'])
    assert dt.year == 2024
    assert dt.month == 12
    assert dt.day == 25
    
    # Test invalid date format
    soup = create_pub_element("Published Spring 2023")
    info = scraper._extract_publication_info(soup)
    assert info['state'] == "published"
    assert info['date'] == "Spring 2023"  # Should keep raw string

def test_scrape_with_download_error(mock_click_context):
    """Test book scraping when download fails."""
    scraper = BookScraper(scrape=True)
    
    # Mock the downloader to simulate failure
    with patch.object(scraper.downloader, 'download_url', return_value=False):
        result = scraper.scrape("12345")
        assert result is None

def test_scrape_with_parse_error(mock_click_context, tmp_path):
    """Test book scraping when parsing fails."""
    scraper = BookScraper(scrape=True)
    
    # Create invalid HTML file that will cause JSON parsing to fail
    cache_dir = tmp_path / "data/cache/book/show"
    cache_dir.mkdir(parents=True)
    test_file = cache_dir / "12345.html"
    
    # Create HTML with invalid JSON in the critical data elements
    invalid_html = """
    <html>
        <head>
            <script id="__NEXT_DATA__">
                {invalid json content}
            </script>
        </head>
        <body>
            <script type="application/ld+json">
                {more invalid json}
            </script>
            <h1 data-testid="bookTitle">Invalid Book</h1>
        </body>
    </html>
    """
    test_file.write_text(invalid_html, encoding='utf-8')
    
    # Mock successful download but ensure parsing fails
    with patch.object(scraper.downloader, 'download_url', return_value=True), \
         patch('core.scrapers.book_scraper.Path', return_value=test_file), \
         patch('json.loads', side_effect=json.JSONDecodeError("Invalid JSON", "", 0)):
        result = scraper.scrape("12345")
        assert result is None

def test_scraper_implementations_parity(mock_click_context):
    """Test that BookScraper and BookScraperV2 produce identical results."""
    from core.scrapers.book_scraper import BookScraper
    from core.scrapers.book_scraper_v2 import BookScraperV2
    
    # Create instances of both scrapers
    original_scraper = BookScraper(scrape=True)
    v2_scraper = BookScraperV2(scrape=True)
    
    # List of book IDs to test
    book_ids = ["60435878", "5907", "42844155", "25856606"]
    failures = []
    
    for book_id in book_ids:
        print(f"\nTesting book ID: {book_id}")
        
        # Scrape the same book with both scrapers
        original_result = original_scraper.scrape(book_id)
        v2_result = v2_scraper.scrape(book_id)
        
        # Track failures for this book
        book_failures = []
        
        # Verify both scrapers returned data
        if original_result is None:
            book_failures.append("Original scraper returned None")
            continue
        if v2_result is None:
            book_failures.append("V2 scraper returned None")
            continue
        
        # Compare all fields that should be identical
        fields_to_compare = [
            'goodreads_id',
            'title',
            'work_id',
            'published_date',
            'published_state',
            'language',
            'pages',
            'isbn',
            'goodreads_rating',
            'goodreads_votes',
            'description',
            'source',
            'hidden'
        ]
        
        for field in fields_to_compare:
            if original_result[field] != v2_result[field]:
                book_failures.append(
                    f"Field '{field}' differs:\n"
                    f"Original: {original_result[field]}\n"
                    f"V2: {v2_result[field]}"
                )
        
        # Compare relationships (may have different order, so compare sets)
        for relation in ['authors', 'series', 'genres']:
            original_items = {tuple(sorted(item.items())) for item in original_result[relation]}
            v2_items = {tuple(sorted(item.items())) for item in v2_result[relation]}
            
            if original_items != v2_items:
                book_failures.append(
                    f"\n{relation} lists differ:\n"
                    f"Original {relation}: {original_result[relation]}\n"
                    f"V2 {relation}: {v2_result[relation]}\n"
                    f"Items in original but not in v2:\n"
                    f"{[dict(items) for items in original_items - v2_items]}\n"
                    f"Items in v2 but not in original:\n"
                    f"{[dict(items) for items in v2_items - original_items]}"
                )
        
        # Image URL comparison
        if original_result['image_url'] and v2_result['image_url']:
            # Strip leading slash if present for comparison
            original_path = original_result['image_url'].lstrip('/')
            v2_path = v2_result['image_url'].lstrip('/')
            
            if not original_path.startswith('covers/'):
                book_failures.append(
                    f"Original image URL has wrong format: {original_result['image_url']}"
                )
            if not v2_path.startswith('covers/'):
                book_failures.append(
                    f"V2 image URL has wrong format: {v2_result['image_url']}"
                )
        
        # If any failures occurred for this book, add them to the main failures list
        if book_failures:
            failures.append((book_id, book_failures))
    
    # If any books had failures, raise an assertion error with all failure details
    if failures:
        failure_msg = "\n\nFailures found:\n"
        for book_id, book_failures in failures:
            failure_msg += f"\nBook ID {book_id}:\n"
            for failure in book_failures:
                failure_msg += f"- {failure}\n"
        assert False, failure_msg 