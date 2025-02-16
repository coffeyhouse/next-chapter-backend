# cli/commands/list.py
import click
from sqlalchemy.orm import Session
from core.sa.database import Database
from core.resolvers.book_creator import BookCreator
from core.scrapers.list_scraper import ListScraper
from ..utils import ProgressTracker, print_sync_start, create_progress_bar

@click.group()
def list():
    """List management commands"""
    pass

@list.command()
@click.option('--source', required=True, help='Goodreads list ID to sync')
@click.option('--limit', default=None, type=int, help='Limit number of books to sync')
@click.option('--max-pages', default=1, type=int, help='Maximum number of list pages to scrape')
@click.option('--scrape/--no-scrape', default=False, help='Whether to scrape live or use cached data')
@click.option('--verbose/--no-verbose', default=False, help='Show detailed progress')
def sync_sa(source: str, limit: int, max_pages: int, scrape: bool, verbose: bool):
    """Sync books from a Goodreads list using SQLAlchemy
    
    This command uses the SQLAlchemy-based BookCreator to import books from a Goodreads list.
    It will create book records with proper relationships for authors, genres, and series.
    
    Example:
        cli list sync-sa --source 196307 --scrape  # Sync first page of list ID 196307
        cli list sync-sa --source 196307 --max-pages 3  # Sync first 3 pages
        cli list sync-sa --source 196307 --limit 10  # Sync first 10 books from list
    """
    # Print initial sync information
    print_sync_start(None, limit, source, None, 'list books', verbose)

    # Initialize database and session
    db = Database()
    session = Session(db.engine)
    
    try:
        # Create services
        creator = BookCreator(session, scrape=scrape)
        list_scraper = ListScraper(scrape=scrape)
        
        # Initialize progress tracker
        tracker = ProgressTracker(verbose)
        
        # Get books from list
        list_books = list_scraper.scrape_list(source, max_pages=max_pages)
        if not list_books:
            click.echo(click.style(f"\nNo books found in list: {source}", fg='red'))
            return
            
        if limit:
            list_books = list_books[:limit]
            
        if verbose:
            click.echo(click.style(f"\nFound {len(list_books)} books to sync", fg='blue'))
        
        # Process each book
        with create_progress_bar(list_books, verbose, 'Processing books', 
                               lambda b: b['title']) as book_iter:
            for book_data in book_iter:
                try:
                    # First get the full book data using resolver
                    book_details = creator.resolver.resolve_book(book_data['goodreads_id'])
                    if not book_details:
                        tracker.add_skipped(book_data['title'], book_data['goodreads_id'],
                                        "Failed to get book details", 'red')
                        continue

                    # Create the book using the resolved details
                    book = creator.create_book_from_goodreads(book_details['goodreads_id'], source=f'list_{source}')
                    if book:
                        tracker.increment_imported()
                    else:
                        tracker.add_skipped(book_data['title'], book_data['goodreads_id'],
                                        "Book already exists or was previously scraped")
                except Exception as e:
                    tracker.add_skipped(book_data['title'], book_data['goodreads_id'],
                                    f"Error: {str(e)}", 'red')
        
        # Print results
        tracker.print_results('books')
                      
    except Exception as e:
        click.echo("\n" + click.style(f"Error during sync: {str(e)}", fg='red'), err=True)
        raise
    finally:
        session.close()

if __name__ == '__main__':
    list() 