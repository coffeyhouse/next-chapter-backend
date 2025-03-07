import click
from sqlalchemy.orm import Session
from core.sa.database import Database
from core.scrapers.similar_scraper import SimilarScraper
from core.sa.repositories.book import BookRepository
from core.sa.models import BookSimilar
from ..utils import ProgressTracker, print_sync_start, create_progress_bar
from core.utils.book_sync_helper import process_book_ids
from datetime import datetime, UTC

@click.group()
def similar():
    """Similar books management commands"""
    pass

@similar.command()
@click.option('--limit', default=None, type=int, help='Limit number of books to process')
@click.option('--source', default=None, help='Only sync similar books for books from this source (e.g. library)')
@click.option('--goodreads-id', default=None, help='Sync similar books for a specific book by Goodreads ID')
@click.option('--scrape/--no-scrape', default=False, help='Whether to scrape live or use cached data')
@click.option('--verbose/--no-verbose', default=False, help='Show detailed progress')
@click.option('--retry/--no-retry', default=True, help='Whether to retry failed book creation')
def sync_sa(limit: int, source: str, goodreads_id: str, scrape: bool, verbose: bool, retry: bool):
    """Sync similar books relationships using SQLAlchemy

    This command finds and creates relationships between similar books using Goodreads data.

    Example:
        cli similar sync-sa --source library  # Sync similar books for library books
        cli similar sync-sa --limit 10 --scrape  # Sync 10 books with fresh data
        cli similar sync-sa --goodreads-id 18541  # Sync similar books for specific book
    """
    # Print initial sync information
    print_sync_start(None, limit, source, goodreads_id, 'books', verbose)

    # Initialize database and session
    db = Database()
    session = Session(db.engine)

    try:
        # Create repositories and services
        book_repo = BookRepository(session)
        similar_scraper = SimilarScraper(scrape=scrape)

        # Initialize progress tracker
        tracker = ProgressTracker(verbose)

        # Get books to process
        if goodreads_id:
            # Get specific book
            book = book_repo.get_by_goodreads_id(goodreads_id)
            if not book:
                click.echo(click.style(f"\nNo book found with ID: {goodreads_id}", fg='red'))
                return
            books_to_process = [book]
        else:
            # Get books without similar books processed
            books_to_process = book_repo.get_books_without_similar(source)
            if limit:
                books_to_process = books_to_process[:limit]

        if verbose:
            click.echo(click.style(f"\nFound {len(books_to_process)} books to process", fg='blue'))

        # Process each book
        with create_progress_bar(books_to_process, verbose, 'Processing books', lambda b: b.title) as books_iter:
            for book in books_iter:
                try:
                    # Get similar books data
                    similar_books = similar_scraper.scrape_similar_books(book.work_id)
                    if not similar_books:
                        tracker.add_skipped(book.title, book.goodreads_id,
                                            "Failed to get similar books data", 'red')
                        tracker.increment_processed()
                        continue

                    # Process similar books in bulk using the helper function.
                    similar_ids = [sb['goodreads_id'] for sb in similar_books]
                    created_similar_books = process_book_ids(session, similar_ids, source='similar', scrape=scrape)

                    # For each similar book returned, create a relationship if it doesn't already exist.
                    for similar_book in created_similar_books:
                        if not session.query(BookSimilar).filter_by(
                            work_id=book.work_id,
                            similar_work_id=similar_book.work_id
                        ).first():
                            similar_rel = BookSimilar(
                                work_id=book.work_id,
                                similar_work_id=similar_book.work_id
                            )
                            session.add(similar_rel)
                            session.commit()
                            tracker.increment_imported()

                    book.similar_synced_at = datetime.now(UTC)
                    session.commit()
                    tracker.increment_processed()

                except Exception as e:
                    tracker.add_skipped(book.title, book.goodreads_id,
                                        f"Error: {str(e)}", 'red')
                    tracker.increment_processed()

        # Print results
        tracker.print_results('books')

    except Exception as e:
        click.echo("\n" + click.style(f"Error during sync: {str(e)}", fg='red'), err=True)
        raise
    finally:
        session.close()

if __name__ == '__main__':
    similar()
