# core/resolvers/book_resolver.py

from core.scrapers.book_scraper import BookScraper
from core.scrapers.editions_scraper import EditionsScraper

class BookResolver:
    def __init__(self, scrape: bool = False):
        self.book_scraper = BookScraper(scrape=scrape)
        self.editions_scraper = EditionsScraper(scrape=scrape)

    def resolve_book(self, goodreads_id: str) -> dict:
        """
        Resolves the final book data by:
          1. Scraping the main book page using the given Goodreads id.
          2. Scraping the editions page using the work id from the main book data.
          3. Choosing the first edition from the editions result.
          4. Fully scraping that chosen edition page (using its Goodreads id) to
             get complete details, which replace the original book data.
        
        Returns:
            A dictionary with the final, fully scraped book details, or None if no editions found.
        """
        # Step 1: Scrape the main book page.
        main_book_data = self.book_scraper.scrape(goodreads_id)
        if not main_book_data:
            print(f"Failed to scrape the main book page for ID: {goodreads_id}")
            return None

        # Step 2: Use the work id from the main book data to scrape the editions page.
        work_id = main_book_data.get('work_id')
        if not work_id:
            print("No work id found")
            return None

        editions = self.editions_scraper.scrape_editions(work_id)
        if not editions:
            print("No editions found")
            return None

        # Step 3: Choose the first edition from the list.
        chosen_edition = editions[0]
        chosen_goodreads_id = chosen_edition.get('goodreads_id')
        if not chosen_goodreads_id:
            print("Chosen edition has no Goodreads id")
            return None

        # Step 4: Fully scrape the chosen edition page.
        final_book_data = self.book_scraper.scrape(chosen_goodreads_id)
        if not final_book_data:
            print("Failed to fully scrape chosen edition")
            return None

        return final_book_data
