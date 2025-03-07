# core/scrapers/list_scraper.py
from bs4 import BeautifulSoup
import re
from typing import Dict, Any, List, Optional
from .base_scraper import BaseScraper

class ListScraper(BaseScraper):
    """Scraper for list pages on Goodreads."""
    
    def __init__(self, scrape: bool = False):
        """
        Initialize the list scraper.
        
        Args:
            scrape: Whether to allow live scraping
        """
        super().__init__(scrape=scrape)
    
    def get_url(self, list_id: str) -> str:
        """Get URL for list page"""
        return self.get_page_url(list_id, 1)
    
    def get_page_url(self, list_id: str, page: int) -> str:
        """Get URL for list page with pagination"""
        base_url = f"https://www.goodreads.com/list/show/{list_id}"
        if page > 1:
            return f"{base_url}?page={page}"
        return base_url
    
    def get_pagination_params(self, page: int) -> Dict[str, Any]:
        """Get pagination parameters for URL"""
        # Only include page parameter for pages after first
        if page > 1:
            return {'page': page}
        return {}
    
    def get_cache_path(self, identifier: str, subdir: str = '', suffix: str = '.html') -> str:
        """Override to handle the specific cache path format for lists"""
        path = self.cache_dir
        
        # First page doesn't have page parameter in URL
        if identifier.endswith('_page_1'):
            base_id = identifier.replace('_page_1', '')
            return path / f"{base_id}.html"
            
        # For other pages, include the page parameter
        if '_page_' in identifier:
            base_id, page = identifier.split('_page_')
            return path / f"{base_id}page={page}.html"
            
        return path / f"{identifier}{suffix}"
    
    def extract_data(self, soup: BeautifulSoup, list_id: str) -> Dict[str, Any]:
        """Extract data from a single page"""
        books = self.extract_page_data(soup, list_id)
        
        return {
            'list_id': list_id,
            'books': books
        }
    
    def extract_page_data(self, soup: BeautifulSoup, list_id: str) -> List[Dict[str, Any]]:
        """Extract books from list page"""
        books = []
        book_rows = soup.find_all('tr', itemtype="http://schema.org/Book")
        
        if not book_rows:
            self.logger.warning(f"No book rows found for list: {list_id}")
            return []
            
        self.logger.info(f"Found {len(book_rows)} book rows")
        
        for row in book_rows:
            book = {
                'goodreads_id': None,
                'title': None,
                'author': {
                    'goodreads_id': None,
                    'name': None
                },
                'rating': None,
                'rating_count': None,
                'score': None,
                'votes': None
            }
            
            # Get book ID and title
            title_link = row.find('a', class_='bookTitle')
            if title_link:
                book['title'] = title_link.find('span', itemprop='name').text.strip()
                url_match = re.search(r'/show/(\d+)', title_link['href'])
                if url_match:
                    book['goodreads_id'] = url_match.group(1)
            
            # Get author info
            author_link = row.find('a', class_='authorName')
            if author_link:
                book['author']['name'] = author_link.find('span', itemprop='name').text.strip()
                author_url_match = re.search(r'/author/show/(\d+)', author_link['href'])
                if author_url_match:
                    book['author']['goodreads_id'] = author_url_match.group(1)
            
            # Get rating and rating count
            rating_text = row.find('span', class_='minirating')
            if rating_text:
                text = rating_text.text.strip()
                rating_match = re.search(r'(\d+\.\d+)\s*avg rating\s*—\s*([\d,]+)\s*ratings', text)
                if rating_match:
                    book['rating'] = float(rating_match.group(1))
                    book['rating_count'] = int(rating_match.group(2).replace(',', ''))
            
            # Get score and votes
            score_text = row.find('a', onclick=lambda x: x and 'score_explanation' in x)
            if score_text:
                score_match = re.search(r'score:\s*([\d,]+)', score_text.text)
                if score_match:
                    book['score'] = int(score_match.group(1).replace(',', ''))
            
            votes_text = row.find('a', id=lambda x: x and x.startswith('loading_link_'))
            if votes_text:
                votes_match = re.search(r'(\d+)\s*people voted', votes_text.text)
                if votes_match:
                    book['votes'] = int(votes_match.group(1))
            
            # Only add if we have the essential data
            if book['goodreads_id'] and book['title']:
                books.append(book)
        
        return books
    
    # Legacy method for backward compatibility
    def scrape_list(self, list_id: str, max_pages: int = 1) -> List[Dict[str, Any]]:
        """
        Get books from a list page
        Args:
            list_id: The Goodreads list ID
            max_pages: Maximum number of pages to scrape (default: 1)
        
        Returns list of books with format:
        [
            {
                'goodreads_id': str,
                'title': str,
                'author': {
                    'goodreads_id': str,
                    'name': str
                },
                'rating': float,
                'rating_count': int,
                'score': int,
                'votes': int
            }
        ]
        """
        self.logger.info(f"Scraping list: {list_id}")
        
        # Handle first page
        result = self.scrape(list_id)
        if not result or not result.get('books'):
            self.logger.warning(f"No books found in list: {list_id}")
            return []
            
        books = result['books']
        
        # Handle additional pages if requested
        current_page = 1
        while current_page < max_pages:
            current_page += 1
            page_result = self.scrape(f"{list_id}_page_{current_page}")
            
            if not page_result or not page_result.get('books'):
                break
                
            books.extend(page_result['books'])
            
        self.logger.info(f"Found {len(books)} books in list")
        return books