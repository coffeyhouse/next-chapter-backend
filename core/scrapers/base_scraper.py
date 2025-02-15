from bs4 import BeautifulSoup
from pathlib import Path
import logging
from typing import Optional, Union
import click
from abc import ABC, abstractmethod
from ..utils.http import GoodreadsDownloader

class BaseScraper(ABC):
    """Base class for all scrapers providing common functionality."""
    
    def __init__(self, scrape: bool = False, cache_dir: Union[str, Path] = 'data/cache'):
        """
        Initialize the base scraper.
        
        Args:
            scrape: Whether to allow live scraping or use only cached data
            cache_dir: Base directory for caching scraped data
        """
        self.downloader = GoodreadsDownloader(scrape)
        self.cache_dir = Path(cache_dir)
        self._setup_logging()
    
    def _setup_logging(self):
        """Set up logging for the scraper."""
        self.logger = logging.getLogger(self.__class__.__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def download_url(self, url: str, identifier: str, retries: int = 3) -> bool:
        """
        Download a URL and cache the response.
        
        Args:
            url: The URL to download
            identifier: Unique identifier for caching
            retries: Number of download attempts before giving up
            
        Returns:
            bool: True if download was successful, False otherwise
        """
        if click.get_current_context().find_root().params.get('verbose', False):
            click.echo(click.style(f"Downloading: {url}", fg='cyan'))
            
        attempt = 0
        while attempt < retries:
            try:
                success = self.downloader.download_url(url)
                if success:
                    return True
                attempt += 1
                self.logger.warning(f"Download attempt {attempt} failed for {url}")
            except Exception as e:
                self.logger.error(f"Error downloading {url}: {e}")
                attempt += 1
        
        self.logger.error(f"Failed to download {url} after {retries} attempts")
        return False
    
    def read_cache(self, cache_path: Union[str, Path]) -> Optional[str]:
        """
        Read HTML content from cache.
        
        Args:
            cache_path: Path to the cached file
            
        Returns:
            str: The cached HTML content, or None if not found/error
        """
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            self.logger.warning(f"Cache file not found: {cache_path}")
            return None
        except PermissionError:
            self.logger.error(f"Permission denied reading cache: {cache_path}")
            return None
        except Exception as e:
            self.logger.error(f"Error reading cache {cache_path}: {e}")
            return None
    
    def write_cache(self, cache_path: Union[str, Path], content: str) -> bool:
        """
        Write content to cache.
        
        Args:
            cache_path: Path where to write the cache file
            content: The content to cache
            
        Returns:
            bool: True if write was successful, False otherwise
        """
        try:
            cache_path = Path(cache_path)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            self.logger.error(f"Error writing cache {cache_path}: {e}")
            return False
    
    def get_cache_path(self, identifier: str, subdir: str = '', suffix: str = '.html') -> Path:
        """
        Get the cache file path for an identifier.
        
        Args:
            identifier: Unique identifier for the item
            subdir: Optional subdirectory within cache
            suffix: File suffix to use
            
        Returns:
            Path: The constructed cache path
        """
        path = self.cache_dir
        if subdir:
            path = path / subdir
        return path / f"{identifier}{suffix}"
    
    def parse_html(self, html: str) -> Optional[BeautifulSoup]:
        """
        Parse HTML content into a BeautifulSoup object.
        
        Args:
            html: The HTML content to parse
            
        Returns:
            BeautifulSoup: The parsed HTML, or None if parsing failed
        """
        if not html:
            return None
            
        try:
            return BeautifulSoup(html, 'html.parser')
        except Exception as e:
            self.logger.error(f"Error parsing HTML: {e}")
            return None
    
    def clean_html(self, html: str) -> str:
        """
        Clean HTML content before parsing.
        Can be overridden by derived classes for specific cleaning needs.
        
        Args:
            html: The HTML content to clean
            
        Returns:
            str: The cleaned HTML
        """
        return html
    
    @abstractmethod
    def get_url(self, identifier: str) -> str:
        """
        Get the URL for an identifier.
        Must be implemented by derived classes.
        
        Args:
            identifier: The identifier to get the URL for
            
        Returns:
            str: The constructed URL
        """
        pass
    
    def scrape(self, identifier: str) -> Optional[dict]:
        """
        Main scraping method that coordinates the scraping process.
        
        Args:
            identifier: The identifier of the item to scrape
            
        Returns:
            dict: The scraped data, or None if scraping failed
        """
        # Get URL and attempt download
        url = self.get_url(identifier)
        if not self.download_url(url, identifier):
            self.logger.error(f"Failed to download {url}")
            return None
        
        # Read from cache
        cache_path = self.get_cache_path(identifier)
        html = self.read_cache(cache_path)
        if not html:
            self.logger.error(f"Failed to read cache for {identifier}")
            return None
        
        # Clean and parse HTML
        html = self.clean_html(html)
        soup = self.parse_html(html)
        if not soup:
            self.logger.error(f"Failed to parse HTML for {identifier}")
            return None
        
        # Extract data (to be implemented by derived classes)
        try:
            return self.extract_data(soup, identifier)
        except Exception as e:
            self.logger.error(f"Error extracting data for {identifier}: {e}")
            return None
    
    @abstractmethod
    def extract_data(self, soup: BeautifulSoup, identifier: str) -> dict:
        """
        Extract data from parsed HTML.
        Must be implemented by derived classes.
        
        Args:
            soup: The parsed HTML
            identifier: The identifier being scraped
            
        Returns:
            dict: The extracted data
        """
        pass 