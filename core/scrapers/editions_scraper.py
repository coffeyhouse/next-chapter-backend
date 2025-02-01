# core/scrapers/editions_scraper.py
class EditionsScraper:
    """Scrapes editions from a Goodreads work page"""
    
    def scrape_editions(self, work_id: str) -> list[dict]:
        """
        Get all editions of a work
        Returns list of editions in same format as book scraper
        Makes it easy to use the edition data directly
        """