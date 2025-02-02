# core/scrapers/similar_scraper.py
from bs4 import BeautifulSoup
from pathlib import Path
import re
from ..utils.http import GoodreadsDownloader

class SimilarScraper:
    """Scrapes similar books from Goodreads"""
    
    def __init__(self, scrape: bool = False):
        self.downloader = GoodreadsDownloader(scrape)
    
    def scrape_similar_books(self, book_id: str) -> list[dict]:
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
        print(f"Scraping similar books for: {book_id}")
        
        # Get page content
        url = self._get_page_url(book_id)
        if not self.downloader.download_url(url):
            print(f"Failed to download similar books page for ID: {book_id}")
            return []
            
        # Read the downloaded page
        html = self._read_html(book_id)
        if not html:
            return []
            
        try:
            soup = BeautifulSoup(html, 'html.parser')
            return self._extract_similar_books(soup)
            
        except Exception as e:
            print(f"Error processing similar books: {e}")
            return []
    
    def _get_page_url(self, book_id: str) -> str:
        """Get URL for similar books page"""
        return f"https://www.goodreads.com/book/similar/{book_id}"
    
    def _read_html(self, book_id: str) -> str:
        """Read downloaded HTML file"""
        path = Path('data/cache/book/similar') / f"{book_id}.html"
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading HTML file: {e}")
            return None
    
    def _extract_similar_books(self, soup) -> list:
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