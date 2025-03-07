# core/scrapers/author_scraper.py
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
from .base_scraper import BaseScraper
from ..utils.image import download_author_photo

class AuthorScraper(BaseScraper):
    """Scraper for author pages on Goodreads."""
    
    def __init__(self, scrape: bool = False):
        """
        Initialize the author scraper.
        
        Args:
            scrape: Whether to allow live scraping
        """
        super().__init__(scrape=scrape)
    
    def get_url(self, author_id: str) -> str:
        """Get Goodreads URL for author"""
        return f"https://www.goodreads.com/author/show/{author_id}"
    
    def extract_data(self, soup: BeautifulSoup, author_id: str) -> Dict[str, Any]:
        """Extract author data from parsed HTML"""
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
    
    def _extract_name(self, soup) -> Optional[str]:
        """Extract author name"""
        name_element = soup.find('h1', class_='authorName')
        if name_element:
            name_span = name_element.find('span', itemprop='name')
            if name_span:
                return ' '.join(name_span.text.split())
        return None
    
    def _extract_bio(self, soup) -> Optional[str]:
        """Extract author biography"""
        bio_div = soup.find('div', class_='aboutAuthorInfo')
        if bio_div:
            bio_span = bio_div.find('span', id=lambda x: x and x.startswith('freeTextContainer'))
            if bio_span:
                return bio_span.text.strip()
        return None
    
    def _extract_photo_url(self, soup) -> Optional[str]:
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
    
    # Legacy method for backward compatibility
    def scrape_author(self, author_id: str) -> Optional[Dict[str, Any]]:
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
        self.logger.info(f"Scraping author: {author_id}")
        return self.scrape(author_id)