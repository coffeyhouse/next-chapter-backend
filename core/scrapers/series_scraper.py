# core/scrapers/series_scraper.py
class SeriesScraper:
    """Scrapes series information and books"""
    
    def scrape_series(self, series_id: str) -> dict:
        """
        Get series info and books
        Expected output:
        {
            'goodreads_id': str,
            'name': str,
            'books': [
                {
                    'goodreads_id': str,
                    'title': str,
                    'order': float
                }
            ]
        }
        """