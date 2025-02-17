# core/scrapers/editions_scraper.py
from bs4 import BeautifulSoup
from pathlib import Path
import re
from urllib.parse import urlencode
from ..utils.http import GoodreadsDownloader

class EditionsScraper:
    """Scrapes editions from a Goodreads work page"""
    
    def __init__(self, scrape: bool = False):
        self.downloader = GoodreadsDownloader(scrape)
        self.has_english_editions = False
        self.has_valid_format = False
        self.has_page_count = False
        self.has_valid_publication = False
    
    def scrape_editions(self, work_id: str) -> list[dict]:
        """
        Get editions from first page of a work
        Returns list of editions with format:
        [
            {
                'goodreads_id': str,
                'title': str,
                'format': str,  # Paperback, Hardcover, etc.
                'pages': int,
                'published_date': str,
                'language': str,
                'rating': float,
                'rating_count': int
            }
        ]
        """
        # Reset all flags
        self.has_english_editions = False
        self.has_valid_format = False
        self.has_page_count = False
        self.has_valid_publication = False
        
        # Get first page content
        url = self._get_page_url(work_id, 1)
        if not self.downloader.download_url(url):
            return []
        
        # Read the downloaded page
        html = self._read_html(work_id, 1)
        if not html:
            return []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            editions = self._extract_editions(soup)
            return editions
            
        except Exception as e:
            print(f"Error processing page: {e}")
            return []
    
    def _get_page_url(self, work_id: str, page: int) -> str:
        """Get URL for editions page"""
        base = f"https://www.goodreads.com/work/editions/{work_id}"
        params = {
            'page': page,
            'per_page': 100,
            'utf8': '✓',
            'expanded': 'true'
        }
        return f"{base}?{urlencode(params)}"
    
    def _read_html(self, work_id: str, page: int) -> str:
        """Read downloaded HTML file"""
        query = f"page={page}&per_page=100&utf8=%E2%9C%93&expanded=true"
        path = Path('data/cache/work/editions') / f"{work_id}{query}.html"
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading HTML file: {e}")
            return None
    
    def _extract_editions(self, soup) -> list:
        """Extract editions from page"""
        editions = []
        edition_elements = soup.find_all('div', class_='elementList clearFix')
        
        valid_formats = ['Kindle Edition', 'Paperback', 'Hardcover', 'Mass Market Paperback', 'ebook']
        
        for element in edition_elements:
            edition = {
                'goodreads_id': None,
                'title': None,
                'format': None,
                'pages': None,
                'published_date': None,
                'language': None,
                'rating': None,
                'rating_count': None
            }
            
            # Get ID and title
            book_link = element.find('a', class_='bookTitle')
            if book_link:
                edition['title'] = book_link.text.strip()
                url_match = re.search(r'/show/(\d+)', book_link['href'])
                if url_match:
                    edition['goodreads_id'] = url_match.group(1)
            
            # Get other details
            details = element.find('div', class_='editionData')
            if details:
                # Get format and pages
                format_div = details.find('div', text=re.compile(r'(Paperback|Hardcover|Kindle Edition|ebook|Mass Market Paperback).*pages?', re.IGNORECASE))
                if format_div:
                    text = format_div.text.strip()
                    format_match = re.search(r'(Paperback|Hardcover|Kindle Edition|ebook|Mass Market Paperback)', text, re.IGNORECASE)
                    if format_match:
                        edition['format'] = format_match.group(1)
                        # Track if we've found a valid format
                        if edition['format'] in valid_formats:
                            self.has_valid_format = True
                    
                    pages_match = re.search(r'(\d+)\s*pages?', text)
                    if pages_match:
                        edition['pages'] = int(pages_match.group(1))
                        # Track if we've found any page counts
                        if edition['pages'] > 0:
                            self.has_page_count = True
                
                # Get published date
                pub_div = details.find('div', text=re.compile(r'Published|Expected publication'))
                if pub_div:
                    text = pub_div.text.strip()
                    # Extract date portion, excluding "by Publisher" text
                    date_match = re.search(r'(?:Published|Expected publication)\s+(.*?)(?:\s+by\s+.*)?$', text)
                    if date_match:
                        date_text = date_match.group(1).strip()
                        # Only set if it looks like a real date (not just "by Publisher")
                        if not date_text.startswith('by '):
                            edition['published_date'] = date_text
                            # Track if we've found any valid publication dates
                            self.has_valid_publication = True
                
                # Get language
                language_div = details.find('div', text=lambda x: x and 'Edition language:' in x)
                if language_div and language_div.find_next('div', class_='dataValue'):
                    edition['language'] = language_div.find_next('div', class_='dataValue').text.strip()
                    # Track if we've found any English editions
                    if edition['language'] == 'English':
                        self.has_english_editions = True
                
                # Get rating and rating count
                rating_div = details.find('div', text=lambda x: x and 'Average rating:' in x)
                if rating_div:
                    rating_value = rating_div.find_next('div', class_='dataValue')
                    if rating_value:
                        text = rating_value.text.strip()
                        rating_match = re.search(r'(\d+\.\d+)\s*\(([0-9,]+)\s*ratings?\)', text)
                        if rating_match:
                            edition['rating'] = float(rating_match.group(1))
                            edition['rating_count'] = int(rating_match.group(2).replace(',', ''))
            
            # Only add if it meets all criteria:
            # - Has goodreads_id and title
            # - Has pages
            # - Has valid published date (not just "by Publisher")
            # - Is in English
            # - Has valid format
            if (edition['goodreads_id'] and edition['title'] and 
                edition['pages'] and
                edition['published_date'] and
                not edition['published_date'].startswith('by ') and
                edition['language'] == 'English' and
                edition['format'] in valid_formats):
                editions.append(edition)
        
        return editions