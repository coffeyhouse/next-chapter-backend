# core/scrapers/author_scraper.py
from bs4 import BeautifulSoup
from pathlib import Path
from ..utils.http import GoodreadsDownloader
from ..utils.image import download_author_photo

class AuthorScraper:
    """Scrapes author details from Goodreads"""
    
    def __init__(self, scrape: bool = False):
        self.downloader = GoodreadsDownloader(scrape)
    
    def scrape_author(self, author_id: str) -> dict:
        """
        Get author data from author page
        Expected output matches authors table schema:
        {
            'goodreads_id': str,
            'name': str,
            'bio': str,
            'image_url': str
        }
        """
        print(f"Scraping author: {author_id}")
        
        # Get author page
        url = self._get_author_url(author_id)
        if not self.downloader.download_url(url):
            print(f"Failed to download author page for ID: {author_id}")
            return None
            
        # Read HTML
        html = self._read_html(author_id)
        if not html:
            return None
            
        try:
            soup = BeautifulSoup(html, 'html.parser')
            author_data = {
                'goodreads_id': author_id,
                'name': self._extract_name(soup),
                'bio': self._extract_bio(soup),
                'image_url': None
            }
            
            # Handle author photo
            photo_url = self._extract_photo_url(soup)
            if photo_url:
                local_path = download_author_photo(author_id, photo_url)
                if local_path:
                    author_data['image_url'] = local_path
            
            return author_data
            
        except Exception as e:
            print(f"Error parsing author data: {e}")
            return None
    
    def _get_author_url(self, author_id: str) -> str:
        """Get Goodreads URL for author"""
        return f"https://www.goodreads.com/author/show/{author_id}"
    
    def _read_html(self, author_id: str) -> str:
        """Read downloaded HTML file"""
        path = Path('data/cache/author/show') / f"{author_id}.html"
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading HTML file: {e}")
            return None
    
    def _extract_name(self, soup) -> str:
        """Extract author name"""
        name_element = soup.find('h1', class_='authorName')
        if name_element:
            name_span = name_element.find('span', itemprop='name')
            if name_span:
                return ' '.join(name_span.text.split())
        return None
    
    def _extract_bio(self, soup) -> str:
        """Extract author biography"""
        bio_div = soup.find('div', class_='aboutAuthorInfo')
        if bio_div:
            bio_span = bio_div.find('span', id=lambda x: x and x.startswith('freeTextContainer'))
            if bio_span:
                return bio_span.text.strip()
        return None
    
    def _extract_photo_url(self, soup) -> str:
        """Extract author photo URL with fallbacks"""
        # Try authorPhotoImg class first
        img = soup.find('img', class_='authorPhotoImg')
        if img and 'src' in img.attrs:
            return img['src']
        
        # Try alt text containing author
        img = soup.find('img', alt=lambda x: x and 'author' in x.lower())
        if img and 'src' in img.attrs:
            return img['src']
        
        # Try leftContainer
        container = soup.find('div', class_='leftContainer authorLeftContainer')
        if container:
            img = container.find('img')
            if img and 'src' in img.attrs:
                return img['src']
        
        return None