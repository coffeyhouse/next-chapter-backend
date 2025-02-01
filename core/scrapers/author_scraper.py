# core/scrapers/author_scraper.py
class AuthorScraper:
    """Scrapes author details from Goodreads"""
    
    def scrape_author(self, author_id: str) -> dict:
        """
        Get author data from author page
        Expected output:
        {
            'goodreads_id': str,
            'name': str,
            'bio': str,
            'image_url': str
        }
        """