# core/scrapers/similar_scraper.py
from bs4 import BeautifulSoup
import re
from typing import Dict, Any, List, Optional
from .base_scraper import BaseScraper

class SimilarScraper(BaseScraper):
    """Scraper for similar books pages on Goodreads."""
    
    def __init__(self, scrape: bool = False):
        """
        Initialize the similar books scraper.
        
        Args:
            scrape: Whether to allow live scraping
        """
        super().__init__(scrape=scrape)
    
    def get_url(self, work_id: str) -> str:
        """Get URL for similar books page"""
        return f"https://www.goodreads.com/book/similar/{work_id}"
    
    def extract_data(self, soup: BeautifulSoup, work_id: str) -> Dict[str, Any]:
        """Extract similar books data from parsed HTML"""
        similar_books = self._extract_similar_books(soup)
        
        return {
            'work_id': work_id,
            'similar_books': similar_books
        }
    
    def _extract_similar_books(self, soup) -> List[Dict[str, Any]]:
        """Extract similar books from page"""
        similar_books = []
        book_divs = soup.find_all('div', class_='u-paddingBottomXSmall')
        
        # Skip first div (it's the source book)
        for div in book_divs[1:]:
            book_link = div.find('a', class_='gr-h3')
            if not book_link:
                continue
                
            book = {
                'goodreads_id': None,
                'title': None
            }
            
            # Get ID from URL
            url_match = re.search(r'/show/(\d+)', book_link['href'])
            if url_match:
                book['goodreads_id'] = url_match.group(1)
            
            # Get title
            title_span = book_link.find('span', itemprop='name')
            if title_span:
                book['title'] = title_span.text.strip()
            
            if book['goodreads_id'] and book['title']:
                similar_books.append(book)
        
        return similar_books
    
    # Legacy method for backward compatibility
    def scrape_similar_books(self, work_id: str) -> List[Dict[str, Any]]:
        """
        Get similar books for a given book
        Returns list of books with format:
        [
            {
                'goodreads_id': str,
                'title': str
            }
        ]
        """
        self.logger.info(f"Scraping similar books for: {work_id}")
        result = self.scrape(work_id)
        return result.get('similar_books', []) if result else []