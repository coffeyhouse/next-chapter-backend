from bs4 import BeautifulSoup
from pathlib import Path
import re
from ..utils.http import GoodreadsDownloader

class ListScraper:
    """Scrapes books from a Goodreads list page"""
    
    def __init__(self, scrape: bool = False):
        self.downloader = GoodreadsDownloader(scrape)
        # Ensure cache directory exists
        cache_dir = Path('data/cache/list/show')
        cache_dir.mkdir(parents=True, exist_ok=True)
    
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
        print(f"Scraping list: {list_id}")
        all_books = []
        current_page = 1
        
        while current_page <= max_pages:
            # Get list page
            url = self._get_page_url(list_id, current_page)
            if not self.downloader.download_url(url):
                print(f"Failed to download list page {current_page} for ID: {list_id}")
                break
            
            # Read HTML
            html = self._read_html(list_id, current_page)
            if not html:
                break
            
            try:
                soup = BeautifulSoup(html, 'html.parser')
                books = self._extract_books(soup)
                if not books:
                    break  # No more books found
                    
                all_books.extend(books)
                
                # Check if there are more pages
                if not self._has_next_page(soup):
                    break
                    
                current_page += 1
                
            except Exception as e:
                print(f"Error processing page {current_page}: {e}")
                break
                
        return all_books
    
    def _get_page_url(self, list_id: str, page: int = 1) -> str:
        """Get URL for list page"""
        base_url = f"https://www.goodreads.com/list/show/{list_id}"
        if page > 1:
            return f"{base_url}?page={page}"
        return base_url
    
    def _read_html(self, list_id: str, page: int = 1) -> str:
        """Read downloaded HTML file"""
        filename = f"{list_id}.html" if page == 1 else f"{list_id}_page_{page}.html"
        path = Path('data/cache/list/show') / filename
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading HTML file: {e}")
            return None
    
    def _has_next_page(self, soup) -> bool:
        """Check if there is a next page"""
        next_link = soup.find('a', class_='next_page')
        return next_link is not None and not 'disabled' in next_link.get('class', [])
    
    def _extract_books(self, soup) -> list:
        """Extract books from list page"""
        books = []
        book_rows = soup.find_all('tr', itemtype="http://schema.org/Book")
        
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