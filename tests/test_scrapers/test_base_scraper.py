import pytest
from pathlib import Path
from bs4 import BeautifulSoup
import click
from unittest.mock import patch, mock_open, Mock
from core.scrapers.base_scraper import BaseScraper

class MockScraper(BaseScraper):
    """Mock implementation of BaseScraper for testing."""
    
    def get_url(self, identifier: str) -> str:
        return f"https://example.com/{identifier}"
    
    def extract_data(self, soup: BeautifulSoup, identifier: str) -> dict:
        try:
            return {
                'id': identifier,
                'title': soup.find('h1').text if soup.find('h1') else None
            }
        except Exception:
            return None

@pytest.fixture
def mock_click_context():
    """Create a mock Click context."""
    ctx = click.Context(click.Command('test'))
    ctx.params = {'verbose': True}
    with ctx:
        yield ctx

@pytest.fixture
def scraper(mock_click_context, tmp_path):
    """Create a test scraper instance."""
    return MockScraper(scrape=True, cache_dir=tmp_path)

def test_initialization(scraper):
    """Test scraper initialization."""
    assert scraper.downloader is not None
    assert isinstance(scraper.cache_dir, Path)
    assert scraper.logger is not None

def test_download_url(scraper):
    """Test URL downloading."""
    # Test successful download
    with patch.object(scraper.downloader, 'download_url', return_value=True):
        assert scraper.download_url("https://example.com/test", "test") is True
    
    # Test failed download with retries
    with patch.object(scraper.downloader, 'download_url', return_value=False):
        assert scraper.download_url("https://example.com/test", "test", retries=2) is False

def test_read_cache(scraper, tmp_path):
    """Test cache reading functionality."""
    test_html = "<html><body>Test content</body></html>"
    
    # Test successful read
    m = mock_open(read_data=test_html)
    with patch('builtins.open', m):
        content = scraper.read_cache(tmp_path / "test.html")
        assert content == test_html
        m.assert_called_once()
    
    # Test file not found
    with patch('builtins.open', side_effect=FileNotFoundError()):
        content = scraper.read_cache(tmp_path / "nonexistent.html")
        assert content is None
    
    # Test permission error
    with patch('builtins.open', side_effect=PermissionError()):
        content = scraper.read_cache(tmp_path / "test.html")
        assert content is None

def test_write_cache(scraper, tmp_path):
    """Test cache writing functionality."""
    test_html = "<html><body>Test content</body></html>"
    test_file = tmp_path / "test.html"
    
    # Test successful write
    assert scraper.write_cache(test_file, test_html) is True
    assert test_file.read_text(encoding='utf-8') == test_html
    
    # Test write with missing directory
    deep_file = tmp_path / "deep" / "path" / "test.html"
    assert scraper.write_cache(deep_file, test_html) is True
    assert deep_file.read_text(encoding='utf-8') == test_html
    
    # Test write permission error
    with patch('builtins.open', side_effect=PermissionError()):
        with patch('pathlib.Path.mkdir', return_value=None):  # Allow directory creation
            assert scraper.write_cache(test_file, test_html) is False

def test_get_cache_path(scraper):
    """Test cache path generation."""
    # Test basic path
    path = scraper.get_cache_path("test123")
    assert path.name == "test123.html"
    
    # Test with subdirectory
    path = scraper.get_cache_path("test123", "subdir")
    assert "subdir" in str(path)
    assert path.name == "test123.html"
    
    # Test with custom suffix
    path = scraper.get_cache_path("test123", suffix=".json")
    assert path.name == "test123.json"

def test_parse_html(scraper):
    """Test HTML parsing."""
    # Test valid HTML
    html = "<html><body><h1>Test</h1></body></html>"
    soup = scraper.parse_html(html)
    assert isinstance(soup, BeautifulSoup)
    assert soup.find('h1').text == "Test"
    
    # Test empty HTML
    assert scraper.parse_html("") is None
    assert scraper.parse_html(None) is None
    
    # Test malformed HTML
    malformed = "<html><body><h1>Test</h2></body>"
    soup = scraper.parse_html(malformed)
    assert isinstance(soup, BeautifulSoup)  # BeautifulSoup handles malformed HTML

def test_clean_html(scraper):
    """Test HTML cleaning."""
    html = "<html><body>Test</body></html>"
    assert scraper.clean_html(html) == html  # Default implementation returns as-is

def test_scrape_integration(scraper):
    """Test full scraping process."""
    test_html = "<html><body><h1>Test Title</h1></body></html>"
    test_id = "test123"
    
    # Mock all the necessary components
    with patch.object(scraper, 'download_url', return_value=True), \
         patch.object(scraper, 'read_cache', return_value=test_html), \
         patch.object(scraper, 'clean_html', return_value=test_html):
        
        # Test successful scrape
        result = scraper.scrape(test_id)
        assert result is not None
        assert result['id'] == test_id
        assert result['title'] == "Test Title"
        
        # Test failed download
        with patch.object(scraper, 'download_url', return_value=False):
            assert scraper.scrape(test_id) is None
        
        # Test failed cache read
        with patch.object(scraper, 'read_cache', return_value=None):
            assert scraper.scrape(test_id) is None
        
        # Test failed parsing
        with patch.object(scraper, 'parse_html', return_value=None):
            assert scraper.scrape(test_id) is None

def test_error_handling(scraper):
    """Test error handling in various scenarios."""
    # Test download error
    with patch.object(scraper.downloader, 'download_url', side_effect=Exception("Network error")):
        assert scraper.download_url("https://example.com/test", "test") is False
    
    # Test parse error
    with patch.object(BeautifulSoup, '__init__', side_effect=Exception("Parse error")):
        assert scraper.parse_html("<html>test</html>") is None
    
    # Test extraction error
    bad_html = "<html><body><h1>Test</h1></body></html>"
    with patch.object(scraper, 'extract_data', side_effect=Exception("Extract error")), \
         patch('builtins.open', mock_open(read_data=bad_html)), \
         patch.object(scraper, 'download_url', return_value=True):
        assert scraper.scrape("test123") is None 