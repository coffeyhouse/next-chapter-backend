# core/scrapers/author_books_scraper.py
class AuthorBooksScraper:
    """Scrapes list of books by an author"""
    
    def scrape_author_books(self, author_id: str) -> dict:
        """
        Get list of all books by author
        Expected output:
        {
            'author_id': str,
            'author_name': str,
            'books': [
                {
                    'goodreads_id': str,
                    'title': str,
                    'published_date': str
                }
            ]
        }
        """