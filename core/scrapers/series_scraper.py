# core/scrapers/series_scraper.py
from bs4 import BeautifulSoup
import re
from typing import Dict, Any, List, Optional
from .base_scraper import BaseScraper

class SeriesScraper(BaseScraper):
    """Scraper for series pages on Goodreads."""
    
    def __init__(self, scrape: bool = False):
        """
        Initialize the series scraper.
        
        Args:
            scrape: Whether to allow live scraping
        """
        super().__init__(scrape=scrape)
    
    def get_url(self, series_id: str) -> str:
        """Get URL for series page"""
        return f"https://www.goodreads.com/series/show/{series_id}"
    
    def extract_data(self, soup: BeautifulSoup, series_id: str) -> Dict[str, Any]:
        """Extract series data from parsed HTML"""
        series_data = {
            'goodreads_id': series_id,
            'name': self._extract_name(soup),
            'books': self._extract_books(soup)
        }
        
        return series_data
    
    def _extract_name(self, soup) -> Optional[str]:
        """Extract series name"""
        title_element = soup.find('h1', class_='gr-h1--serif')
        if title_element:
            name = title_element.text.strip()
            # Remove " Series" from the end if present
            if name.endswith(' Series'):
                name = name[:-7]
            return name
        return None
    
    def _extract_books(self, soup) -> List[Dict[str, Any]]:
        """Extract books in series with order"""
        books = []
        book_divs = soup.find_all('div', class_='listWithDividers__item')
        
        for book_div in book_divs:
            # Get order number
            order = None
            number_heading = book_div.find('h3', class_='gr-h3--noBottomMargin')
            if number_heading:
                number_text = number_heading.text.strip()
                try:
                    if number_text.startswith('Book '):
                        number_text = number_text[5:]
                    if '-' not in number_text:  # Skip ranges like "1-3"
                        order = float(number_text)
                except ValueError:
                    pass
            
            # Get title and ID
            title_link = book_div.find('a', class_='gr-h3--serif')
            if title_link:
                title = title_link.find('span', itemprop='name')
                if title:
                    # Extract ID from URL
                    url_match = re.search(r'/show/(\d+)', title_link['href'])
                    if url_match:
                        books.append({
                            'goodreads_id': url_match.group(1),
                            'title': title.text.strip(),
                            'order': order
                        })
        
        return books
    
    def scrape_series(self, series_id: str) -> Optional[Dict[str, Any]]:
        """
        Get series info and books
        Expected output:
        {
            'goodreads_id': str,
            'name': str, 
            'books': [
                {
                    'goodreads_id': str,
                    'title': str,
                    'order': float
                }
            ]
        }
        """
        self.logger.info(f"Scraping series: {series_id}")
        return self.scrape(series_id)