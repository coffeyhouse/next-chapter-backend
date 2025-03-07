# test_scraper.py
import sys
import json
import argparse
from core.scrapers.book_scraper import BookScraper
from core.scrapers.author_scraper import AuthorScraper
from core.scrapers.author_books_scraper import AuthorBooksScraper
from core.scrapers.series_scraper import SeriesScraper
from core.scrapers.editions_scraper import EditionsScraper
from core.scrapers.similar_scraper import SimilarScraper
from core.scrapers.list_scraper import ListScraper

class EnhancedJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles objects not serializable by default JSON encoder"""
    def default(self, obj):
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)

def get_scraper(scraper_type, scrape=True, max_pages=None):
    """Get a scraper instance for testing"""
    scrapers = {
        'book': BookScraper(scrape=scrape),
        'author': AuthorScraper(scrape=scrape),
        'author_books': AuthorBooksScraper(scrape=scrape, max_pages=max_pages),
        'series': SeriesScraper(scrape=scrape),
        'editions': EditionsScraper(scrape=scrape),
        'similar': SimilarScraper(scrape=scrape),
        'list': ListScraper(scrape=scrape)
    }
    return scrapers[scraper_type]

def scrape_with_legacy_method(scraper_type, item_id, max_pages=None):
    """Use legacy scraping method based on type"""
    scraper = get_scraper(scraper_type, max_pages=max_pages)
    
    if scraper_type == 'book':
        # Call the parent class's scrape method directly for BookScraper
        return super(BookScraper, scraper).scrape(item_id)
    elif scraper_type == 'author':
        return scraper.scrape_author(item_id)
    elif scraper_type == 'author_books':
        return scraper.scrape_author_books(item_id)
    elif scraper_type == 'series':
        return scraper.scrape_series(item_id)
    elif scraper_type == 'editions':
        return scraper.scrape_editions(item_id)
    elif scraper_type == 'similar':
        return scraper.scrape_similar_books(item_id)
    elif scraper_type == 'list':
        return scraper.scrape_list(item_id, max_pages or 1)
    
    return None

def scrape_with_base_method(scraper_type, item_id):
    """Use base class scrape method"""
    scraper = get_scraper(scraper_type)
    # Use direct call to the base class's scrape method
    from core.scrapers.base_scraper import BaseScraper
    return BaseScraper.scrape(scraper, item_id)

def main():
    parser = argparse.ArgumentParser(description='Test Goodreads scrapers')
    parser.add_argument('scraper_type', choices=['book', 'author', 'author_books', 'series', 'editions', 'similar', 'list'], 
                        help='Type of scraper to test')
    parser.add_argument('item_id', help='ID to scrape (book_id, author_id, etc.)')
    parser.add_argument('--use-base', action='store_true', help='Use base class scrape method instead of legacy method')
    parser.add_argument('--no-scrape', action='store_true', help='Use only cached data, no live scraping')
    parser.add_argument('--max-pages', type=int, help='Maximum pages to scrape (for paginated content)')
    parser.add_argument('--output', '-o', help='Output file for JSON results')
    parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON output')
    
    args = parser.parse_args()
    
    try:
        if args.use_base:
            result = scrape_with_base_method(args.scraper_type, args.item_id)
        else:
            # For the book scraper, use a different approach
            if args.scraper_type == 'book':
                book_scraper = BookScraper(scrape=not args.no_scrape)
                # Access the BaseScraper's scrape method directly
                from core.scrapers.base_scraper import BaseScraper
                result = BaseScraper.scrape(book_scraper, args.item_id)
            else:
                result = scrape_with_legacy_method(args.scraper_type, args.item_id, args.max_pages)
        
        if result:
            # Convert result to JSON
            indent = 2 if args.pretty else None
            json_result = json.dumps(result, cls=EnhancedJSONEncoder, indent=indent)
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(json_result)
                print(f"Results saved to {args.output}")
            else:
                print(json_result)
        else:
            print("No data returned from scraper.")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())