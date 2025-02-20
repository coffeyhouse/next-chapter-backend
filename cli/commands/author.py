import click
from sqlalchemy.orm import Session
from core.sa.database import Database
from core.scrapers.author_scraper import AuthorScraper
from core.scrapers.author_books_scraper import AuthorBooksScraper
from core.sa.repositories.author import AuthorRepository
from core.sa.models import Author
from ..utils import ProgressTracker, print_sync_start, create_progress_bar, update_last_synced
from core.utils.book_sync_helper import process_book_ids

@click.group()
def author():
    """Author management commands"""
    pass

@author.command()
@click.option('--days', default=30, help='Sync authors not updated in this many days')
@click.option('--limit', default=None, type=int, help='Limit number of authors to sync')
@click.option('--source', default=None, help='Only sync authors with books from this source (e.g. library)')
@click.option('--goodreads-id', default=None, help='Sync a specific author by Goodreads ID')
@click.option('--scrape/--no-scrape', default=False, help='Whether to scrape live or use cached data')
@click.option('--verbose/--no-verbose', default=False, help='Show detailed progress')
@click.option('--max-pages', default=None, type=int, help='Skip authors with more than this many pages of books')
def sync_sa(days: int, limit: int, source: str, goodreads_id: str, scrape: bool, verbose: bool, max_pages: int):
    """Sync unsynced authors and import their books using SQLAlchemy
    
    This command uses the SQLAlchemy-based BookCreator to import books from authors.
    It will create book records with proper relationships for authors, genres, and series.
    
    Example:
        cli author sync-sa --days 7  # Sync authors not updated in 7 days
        cli author sync-sa --limit 10 --scrape  # Sync 10 authors with fresh data
        cli author sync-sa --source library  # Only sync authors with books from library
        cli author sync-sa --goodreads-id 18541  # Sync specific author by ID
        cli author sync-sa --max-pages 2  # Skip authors with more than 2 pages of books
    """
    # Print initial sync information
    print_sync_start(days, limit, source, goodreads_id, 'authors', verbose)

    # Initialize database and session
    db = Database()
    session = Session(db.engine)
    
    try:
        # Create repositories and services
        author_repo = AuthorRepository(session)
        author_scraper = AuthorScraper(scrape=scrape)
        books_scraper = AuthorBooksScraper(scrape=scrape, max_pages=max_pages)
        
        # Initialize progress tracker
        tracker = ProgressTracker(verbose)
        
        # Get authors to sync
        if goodreads_id:
            # Get or create the specific author
            author = author_repo.get_by_goodreads_id(goodreads_id)
            if not author:
                # Try to get author data to create new author
                author_data = author_scraper.scrape_author(goodreads_id)
                if author_data:
                    author = Author(
                        goodreads_id=goodreads_id,
                        name=author_data.get('name'),
                        bio=author_data.get('bio'),
                        image_url=author_data.get('image_url')
                    )
                    session.add(author)
                    session.commit()
                else:
                    click.echo(click.style(f"\nFailed to find or create author with ID: {goodreads_id}", fg='red'))
                    return
            authors_to_sync = [author]
        else:
            # Get authors that need updating
            authors_to_sync = author_repo.get_unsynced_authors(days, source)
            if limit:
                authors_to_sync = authors_to_sync[:limit]
        
        if verbose:
            click.echo(click.style(f"\nFound {len(authors_to_sync)} authors to sync", fg='blue'))
        
        # Process each author
        with create_progress_bar(authors_to_sync, verbose, 'Processing authors', 
                               lambda a: a.name) as author_iter:
            for author in author_iter:
                try:
                    # Get author data
                    author_data = author_scraper.scrape_author(author.goodreads_id)
                    if not author_data:
                        tracker.add_skipped(author.name, author.goodreads_id, 
                                         "Failed to scrape author data", 'red')
                        continue

                    # Update author details
                    author.bio = author_data.get('bio')
                    author.image_url = author_data.get('image_url')
                    session.commit()

                    # Get author's books
                    books_data = books_scraper.scrape_author_books(author.goodreads_id)
                    if not books_data:
                        tracker.add_skipped(author.name, author.goodreads_id,
                                         "Failed to scrape author's books", 'red')
                        continue

                    # Collect Goodreads IDs from the scraped books and process them at once.
                    goodreads_ids = [b['goodreads_id'] for b in books_data['books']]
                    created_books = process_book_ids(session, goodreads_ids, source='author', scrape=scrape)
                    for _ in created_books:
                        tracker.increment_imported()

                    # Update author last_synced_at
                    update_last_synced(author, session)
                    tracker.increment_processed()
                    
                except Exception as e:
                    tracker.add_skipped(author.name, author.goodreads_id,
                                    f"Error: {str(e)}", 'red')
        
        # Print results
        tracker.print_results('authors')
                      
    except Exception as e:
        click.echo("\n" + click.style(f"Error during sync: {str(e)}", fg='red'), err=True)
        raise
    finally:
        session.close()

if __name__ == '__main__':
    author()