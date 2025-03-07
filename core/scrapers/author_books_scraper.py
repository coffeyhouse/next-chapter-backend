# core/scrapers/author_books_scraper.py
from bs4 import BeautifulSoup
import re
from urllib.parse import urlencode
from typing import Dict, Any, List, Optional
from .base_scraper import BaseScraper

class AuthorBooksScraper(BaseScraper):
    """Scraper for author's books pages on Goodreads."""
    
    def __init__(self, scrape: bool = False, max_pages: int = None):
        """
        Initialize the author books scraper.
        
        Args:
            scrape: Whether to allow live scraping
            max_pages: Maximum number of pages to scrape
        """
        super().__init__(scrape=scrape)
        self.max_pages = max_pages
   
    def get_url(self, author_id: str) -> str:
        """Get URL for author's base page"""
        return self.get_page_url(author_id, 1)
    
    def get_page_url(self, author_id: str, page: int) -> str:
        """Get URL for author's books page"""
        base = f"https://www.goodreads.com/author/list/{author_id}"
        params = {
            'page': page,
            'per_page': 100,
            'utf8': '✓',
            'sort': 'original_publication_year'
        }
        return f"{base}?{urlencode(params)}"
    
    def get_cache_path(self, identifier: str, subdir: str = '', suffix: str = '.html') -> str:
        """Override to handle the specific cache path format for author books"""
        # If there's a page parameter in the identifier
        if '_page_' in identifier:
            author_id, page = identifier.split('_page_')
            query = f"page={page}&per_page=100&utf8=%E2%9C%93&sort=original_publication_year"
            return self.cache_dir / f"{author_id}{query}.html"
        
        # Default case - first page
        query = f"page=1&per_page=100&utf8=%E2%9C%93&sort=original_publication_year"
        return self.cache_dir / f"{identifier}{query}.html"
    
    def extract_data(self, soup: BeautifulSoup, author_id: str) -> Dict[str, Any]:
        """Extract data from single page (first page)"""
        author_name = self._extract_author_name(soup)
        pagination = self.extract_pagination(soup)
        total_pages = pagination['total_pages']
        
        # Check if total pages exceeds max_pages limit
        if self.max_pages and total_pages > self.max_pages:
            self.logger.info(f"Skipping author {author_id} - has {total_pages} pages (max: {self.max_pages})")
            return None
        
        # Get books from first page
        books = self._extract_books(soup)
        
        # Process remaining pages if needed
        current_page = 1
        while current_page < total_pages:
            current_page += 1
            
            # Skip if we've hit max pages
            if self.max_pages and current_page > self.max_pages:
                break
                
            # Get next page
            page_data = self.scrape(f"{author_id}_page_{current_page}")
            if page_data and 'books' in page_data:
                books.extend(page_data['books'])
                self.logger.info(f"Processing page {current_page} of {total_pages}")
            else:
                self.logger.warning(f"Error processing page {current_page}")
                break
        
        # Filter to only include books with dates
        dated_books = [b for b in books if b.get('published_date')]
        
        return {
            'author_id': author_id,
            'author_name': author_name,
            'books': dated_books
        }
    
    def extract_page_data(self, soup: BeautifulSoup, author_id: str) -> List[Dict[str, Any]]:
        """Extract books from page (for pagination)"""
        return self._extract_books(soup)
    
    def extract_metadata(self, soup: BeautifulSoup, author_id: str) -> Dict[str, Any]:
        """Extract author name from page (for pagination)"""
        return {'author_name': self._extract_author_name(soup)}
   
    def _extract_author_name(self, soup) -> Optional[str]:
        """Extract author name"""
        name_link = soup.find('a', class_='authorName')
        if name_link:
            # Clean up extra spaces between words
            return ' '.join(name_link.text.split())
        return None
   
    def _extract_books(self, soup) -> List[Dict[str, Any]]:
        """Extract books from page"""
        books = []
        book_rows = soup.find_all('tr', itemtype='http://schema.org/Book')
        
        for row in book_rows:
            book_link = row.find('a', class_='bookTitle')
            if not book_link:
                continue
               
            # Get title and ID
            book = {
                'title': book_link.find('span', itemprop='name').text.strip(),
                'goodreads_id': None,
                'published_date': None
            }
           
            # Get book ID from URL
            url_match = re.search(r'/show/(\d+)', book_link['href'])
            if url_match:
                book['goodreads_id'] = url_match.group(1)
               
            # Get publication date
            grey_text = row.find('span', class_='greyText smallText uitext')
            if grey_text:
                text = grey_text.get_text(strip=True)
                for prefix in ['expected publication', 'published']:
                    if prefix in text.lower():
                        year_match = re.search(rf'{prefix}\s*(\d{{4}})', text, re.I)
                        if year_match:
                            book['published_date'] = year_match.group(1)
                            break
           
            if book['goodreads_id'] and book['title']:
                books.append(book)
               
        return books
    
    # Legacy method for backward compatibility
    def scrape_author_books(self, author_id: str) -> Optional[Dict[str, Any]]:
        """
        Get list of all books by author
        Expected output:
        {
            'author_id': str,
            'author_name': str,
            'books': [
                {
                    'goodreads_id': str,
                    'title': str,
                    'published_date': str
                }
            ]
        }
        """
        self.logger.info(f"Scraping books for author: {author_id}")
        return self.scrape(author_id)