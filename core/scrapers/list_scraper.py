from bs4 import BeautifulSoup
from pathlib import Path
import re
from .base_scraper import BaseScraper

class ListScraper(BaseScraper):
    """Scrapes books from a Goodreads list page"""
    
    def __init__(self, scrape: bool = False):
        super().__init__(scrape, cache_dir='data/cache/list/show')
    
    def get_url(self, identifier: str) -> str:
        """Get URL for list page (required by BaseScraper)"""
        return self.get_page_url(identifier, 1)
    
    def get_cache_path(self, identifier: str, subdir: str = '', suffix: str = '.html') -> Path:
        """Override cache path to handle first page differently"""
        path = self.cache_dir
        if subdir:
            path = path / subdir
            
        # First page doesn't have page parameter in URL
        if identifier.endswith('_page_1'):
            base_id = identifier.replace('_page_1', '')
            return path / f"{base_id}.html"
            
        # For other pages, include the page parameter
        if '_page_' in identifier:
            base_id, page = identifier.split('_page_')
            return self.cache_dir / f"{base_id}page={page}.html"
            
        return path / f"{identifier}{suffix}"
    
    def extract_data(self, soup: BeautifulSoup, identifier: str) -> dict:
        """Extract data from a single page (required by BaseScraper)"""
        return {
            'items': self.extract_page_data(soup, identifier)
        }
    
    def scrape_list(self, list_id: str, max_pages: int = 1) -> list[dict]:
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
        
        # Use base class pagination
        result = self.scrape_paginated(list_id, max_pages)
        if not result:
            self.logger.warning(f"No results found for list: {list_id}")
            return []
            
        if not result.get('items'):
            self.logger.warning(f"No books found in list: {list_id}")
            return []
            
        self.logger.info(f"Found {len(result['items'])} books in list")
        return result['items']
    
    def get_page_url(self, list_id: str, page: int) -> str:
        """Get URL for list page"""
        base_url = f"https://www.goodreads.com/list/show/{list_id}"
        if page > 1:
            return f"{base_url}?page={page}"
        return base_url
    
    def get_pagination_params(self, page: int) -> dict:
        """Get pagination parameters for URL"""
        # Only include page parameter for pages after first
        if page > 1:
            return {'page': page}
        return {}
    
    def download_url(self, url: str, identifier: str, retries: int = 3) -> bool:
        """Override download to handle rate limiting and retries"""
        self.logger.info(f"Downloading: {url}")
        success = self.downloader.download_url(url)
        if not success:
            self.logger.error(f"Failed to download: {url}")
            return False
        
        # Get the expected cache path
        final_path = self.get_cache_path(identifier)
        
        # Small delay to ensure file is closed
        import time
        time.sleep(0.1)
        
        try:
            # Read from the downloader's cache location
            # For paginated requests, handle both formats
            if '_page_' in identifier:
                base_id, page = identifier.split('_page_')
                temp_path = Path('data/cache/list/show') / f"{base_id}page={page}.html"
            else:
                temp_path = Path('data/cache/list/show') / f"{identifier}.html"
            
            if temp_path.exists():
                # Create parent directories if they don't exist
                final_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Read and write in one go to avoid file locking issues
                with open(temp_path, 'r', encoding='utf-8') as src:
                    content = src.read()
                    
                # Write to the correct final path
                with open(final_path, 'w', encoding='utf-8') as dst:
                    dst.write(content)
                    
                # Also write to base path for first page to maintain compatibility
                if not '_page_' in identifier:
                    base_path = Path('data/cache/list/show') / f"{identifier}.html"
                    if base_path != final_path:
                        with open(base_path, 'w', encoding='utf-8') as base:
                            base.write(content)
                
                self.logger.info(f"Saved cache file to: {final_path}")
                return True
                
            self.logger.error(f"Downloaded file not found: {temp_path}")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to save cache file: {e}")
            return False
    
    def extract_page_data(self, soup: BeautifulSoup, identifier: str) -> list:
        """Extract books from list page"""
        books = []
        book_rows = soup.find_all('tr', itemtype="http://schema.org/Book")
        
        if not book_rows:
            self.logger.warning(f"No book rows found on page: {identifier}")
            return []
            
        self.logger.info(f"Found {len(book_rows)} book rows on page")
        
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