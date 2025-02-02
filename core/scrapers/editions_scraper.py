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
    
    def scrape_editions(self, work_id: str) -> list[dict]:
        """
        Get all editions of a work
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
        print(f"Scraping editions for work: {work_id}")
        editions = []
        current_page = 1
        
        while True:
            # Get page content
            url = self._get_page_url(work_id, current_page)
            if not self.downloader.download_url(url):
                break
            
            # Read the downloaded page
            html = self._read_html(work_id, current_page)
            if not html:
                break
            
            try:
                soup = BeautifulSoup(html, 'html.parser')
                
                # Get editions from this page
                page_editions = self._extract_editions(soup)
                editions.extend(page_editions)
                
                # Check pagination
                pagination = self._extract_pagination(soup)
                print(f"Processing page {pagination['current_page']} of {pagination['total_pages']}")
                
                if current_page >= pagination['total_pages']:
                    break
                
                current_page += 1
                
            except Exception as e:
                print(f"Error processing page {current_page}: {e}")
                break
        
        return editions
    
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
                    
                    pages_match = re.search(r'(\d+)\s*pages?', text)
                    if pages_match:
                        edition['pages'] = int(pages_match.group(1))
                
                # Get published date
                pub_div = details.find('div', text=re.compile(r'Published|Expected publication'))
                if pub_div:
                    text = pub_div.text.strip()
                    # Extract just the date portion
                    date_match = re.search(r'(?:Published|Expected publication)\s+(.*?)(?:\s+by\s+|$)', text)
                    if date_match:
                        edition['published_date'] = date_match.group(1).strip()
                
                # Get language
                language_div = details.find('div', text=lambda x: x and 'Edition language:' in x)
                if language_div and language_div.find_next('div', class_='dataValue'):
                    edition['language'] = language_div.find_next('div', class_='dataValue').text.strip()
                
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
            # - Is in English
            # - Has valid format
            if (edition['goodreads_id'] and edition['title'] and 
                edition['pages'] and
                edition['published_date'] and
                edition['language'] == 'English' and
                edition['format'] in valid_formats):
                editions.append(edition)
        
        return editions
    
    def _extract_pagination(self, soup) -> dict:
        """Extract pagination information"""
        pagination = {'current_page': 1, 'total_pages': 1}
        
        div = soup.find('div', style=lambda x: x and 'text-align: right' in x)
        if div:
            current = div.find('em', class_='current')
            if current:
                try:
                    pagination['current_page'] = int(current.text.strip())
                except ValueError:
                    pass
            
            max_page = 1
            for link in div.find_all('a'):
                try:
                    page_num = int(link.text.strip())
                    max_page = max(max_page, page_num)
                except ValueError:
                    continue
            
            pagination['total_pages'] = max(max_page, pagination['current_page'])
        
        return pagination