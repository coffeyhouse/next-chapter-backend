# core/scrapers/base_scraper.py

from bs4 import BeautifulSoup
from pathlib import Path
import logging
from typing import Optional, Union, Dict, List, Any
import click
from abc import ABC, abstractmethod
import json
import time
from datetime import datetime, timedelta
from urllib.parse import urlencode
import re
from ..utils.http import GoodreadsDownloader

class BaseScraper(ABC):
    """Base class for all scrapers providing common functionality."""
    
    def __init__(self, scrape: bool = False):
        """
        Initialize the base scraper.
        
        Args:
            scrape: Whether to allow live scraping
        """
        self.downloader = GoodreadsDownloader(scrape)
        self.allow_scraping = scrape
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

    def build_url(self, base: str, params: Dict[str, Any]) -> str:
        """
        Construct a URL with query parameters.
        
        Args:
            base: The base URL.
            params: Dictionary of query parameters.
            
        Returns:
            The constructed URL as a string.
        """
        return f"{base}?{urlencode(params)}"

    def download_url(self, url: str) -> Optional[str]:
        """
        Download a URL using an exponential backoff strategy.
        
        Args:
            url: The URL to download.
            
        Returns:
            The downloaded content as a string, or None if download failed.
        """
        try:
            if click.get_current_context().find_root().params.get('verbose', False):
                click.echo(click.style(f"Downloading: {url}", fg='cyan'))
        except RuntimeError:
            # No Click context available, skip verbose output
            pass
            
        # If we can't scrape, return None
        if not self.allow_scraping:
            self.logger.info(f"Skipping download - scraping disabled: {url}")
            return None
            
        attempt = 0
        delay = 1  # initial delay in seconds
        retries = 3
        
        while attempt < retries:
            try:
                success, content = self.downloader.download_url(url)
                if success:
                    return content
                    
                attempt += 1
                self.logger.warning(f"Download attempt {attempt} failed for {url}. Retrying in {delay} seconds.")
                time.sleep(delay)
                delay *= 2  # exponential backoff
            except Exception as e:
                self.logger.error(f"Error downloading {url}: {e}")
                attempt += 1
                time.sleep(delay)
                delay *= 2
        
        self.logger.error(f"Failed to download {url} after {retries} attempts")
        return None

    def parse_html(self, html: str) -> Optional[BeautifulSoup]:
        """
        Parse HTML content into a BeautifulSoup object.
        
        Args:
            html: The HTML content to parse.
            
        Returns:
            A BeautifulSoup object if parsing is successful, otherwise None.
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
            html: The HTML content to clean.
            
        Returns:
            The cleaned HTML as a string.
        """
        return html.strip()

    def extract_json(self, element: Optional[BeautifulSoup], default: Optional[dict] = None) -> dict:
        """
        Safely extract and parse JSON data from a BeautifulSoup element.
        
        Args:
            element: The BeautifulSoup element containing JSON.
            default: Default value to return if extraction fails.
            
        Returns:
            Parsed JSON as a dictionary.
        """
        if element is None:
            return default or {}
        try:
            return json.loads(element.string)
        except Exception as e:
            self.logger.error(f"Error extracting JSON: {e}")
            return default or {}
            
    def extract_id_from_url(self, url: str, pattern: str) -> Optional[str]:
        """
        Extract an ID from a URL using a regex pattern.
        
        Args:
            url: The URL to extract from.
            pattern: Regex pattern to match.
            
        Returns:
            Extracted ID or None if not found.
        """
        match = re.search(pattern, url)
        return match.group(1) if match else None

    @abstractmethod
    def get_url(self, identifier: str) -> str:
        """
        Get the URL for an identifier.
        Must be implemented by derived classes.
        
        Args:
            identifier: The identifier to get the URL for.
            
        Returns:
            The constructed URL as a string.
        """
        pass

    @abstractmethod
    def extract_data(self, soup: BeautifulSoup, identifier: str) -> Dict[str, Any]:
        """
        Extract data from parsed HTML.
        Must be implemented by derived classes.
        
        Args:
            soup: The parsed HTML.
            identifier: The identifier being scraped.
            
        Returns:
            A dictionary containing the extracted data.
        """
        pass

    def scrape(self, identifier: str) -> Optional[Dict[str, Any]]:
        """
        Main scraping method that coordinates the scraping process.
        
        Args:
            identifier: The identifier of the item to scrape.
            
        Returns:
            A dictionary with the scraped data, or None if scraping failed.
        """
        url = self.get_url(identifier)
        html = self.download_url(url)
        
        if not html:
            self.logger.error(f"Failed to download HTML for {identifier}")
            return None
        
        html = self.clean_html(html)
        soup = self.parse_html(html)
        if not soup:
            self.logger.error(f"Failed to parse HTML for {identifier}")
            return None
        
        try:
            return self.extract_data(soup, identifier)
        except Exception as e:
            self.logger.error(f"Error extracting data for {identifier}: {e}")
            return None

    def scrape_paginated(self, identifier: str, max_pages: int = None) -> Optional[Dict[str, Any]]:
        """
        Scrape data from paginated content.
        
        Args:
            identifier: The identifier of the item to scrape
            max_pages: Maximum number of pages to scrape (None for all pages)
            
        Returns:
            Dictionary containing the combined data from all pages, or None if scraping failed
        """
        all_items = []
        current_page = 1
        metadata = {}  # Store any additional data from first page
        
        while True:
            # Check page limit
            if max_pages and current_page > max_pages:
                break
                
            # Get URL for current page
            url = self.get_page_url(identifier, current_page)
            html = self.download_url(url)
            
            if not html:
                if all_items:  # Return what we have if not first page
                    break
                self.logger.error(f"Failed to download page {current_page}")
                return None
                
            html = self.clean_html(html)
            soup = self.parse_html(html)
            if not soup:
                if all_items:
                    break
                return None
            
            try:
                # Extract items from current page
                page_data = self.extract_page_data(soup, identifier)
                if not page_data:
                    break
                    
                # Store metadata from first page
                if current_page == 1:
                    metadata = self.extract_metadata(soup, identifier)
                
                # Add items from this page
                all_items.extend(page_data)
                
                # Check pagination
                pagination = self.extract_pagination(soup)
                if not pagination or current_page >= pagination.get('total_pages', current_page):
                    break
                    
                current_page += 1
                
            except Exception as e:
                self.logger.error(f"Error processing page {current_page}: {e}")
                if all_items:
                    break
                return None
        
        # Combine items with metadata
        return {
            'items': all_items,
            **metadata
        }

    def get_page_url(self, identifier: str, page: int) -> str:
        """
        Get URL for a specific page.
        Default implementation adds page parameter to base URL.
        Can be overridden by derived classes.
        
        Args:
            identifier: The identifier being scraped
            page: The page number
            
        Returns:
            The URL for the specified page
        """
        base_url = self.get_url(identifier)
        params = self.get_pagination_params(page)
        return f"{base_url}?{urlencode(params)}" if params else base_url

    def get_pagination_params(self, page: int) -> Dict[str, Any]:
        """
        Get pagination parameters for URL.
        Can be overridden by derived classes.
        
        Args:
            page: The page number
            
        Returns:
            Dictionary of pagination parameters
        """
        return {
            'page': page
        }

    def extract_page_data(self, soup: BeautifulSoup, identifier: str) -> List[Dict[str, Any]]:
        """
        Extract items from a single page.
        Default implementation returns an empty list.
        Should be overridden by derived classes.
        
        Args:
            soup: The parsed HTML
            identifier: The identifier being scraped
            
        Returns:
            List of items from the page
        """
        return []

    def extract_metadata(self, soup: BeautifulSoup, identifier: str) -> Dict[str, Any]:
        """
        Extract metadata from first page.
        Can be overridden by derived classes.
        
        Args:
            soup: The parsed HTML
            identifier: The identifier being scraped
            
        Returns:
            Dictionary of metadata
        """
        return {}

    def extract_pagination(self, soup: BeautifulSoup) -> Optional[Dict[str, int]]:
        """
        Extract pagination information.
        Can be overridden by derived classes.
        
        Args:
            soup: The parsed HTML
            
        Returns:
            Dictionary with pagination info (e.g., {'current_page': 1, 'total_pages': 10})
        """
        # Default implementation looks for common pagination patterns
        try:
            pagination = {'current_page': 1, 'total_pages': 1}
            
            # Find pagination container
            paginator = soup.find('div', class_=['pagination', 'paginator'])
            if not paginator:
                paginator = soup.find('div', style='float: right')  # Goodreads style
            
            if paginator:
                # Get current page
                current = paginator.find(['em', 'span'], class_='current')
                if current:
                    try:
                        pagination['current_page'] = int(current.text.strip())
                    except ValueError:
                        pass
                
                # Get max page from links
                max_page = 1
                for link in paginator.find_all('a'):
                    try:
                        page_num = int(link.text.strip())
                        max_page = max(max_page, page_num)
                    except ValueError:
                        continue
                
                pagination['total_pages'] = max_page
            
            return pagination
            
        except Exception as e:
            self.logger.error(f"Error extracting pagination: {e}")
            return None