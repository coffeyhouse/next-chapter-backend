import click
from core.database import GoodreadsDB
from sqlalchemy.orm import Session
from core.sa.database import Database
from core.resolvers.book_creator import BookCreator
from core.scrapers.series_scraper import SeriesScraper
from core.sa.repositories.series import SeriesRepository
from core.sa.models import Series
from core.exclusions import should_exclude_book, get_exclusion_reason
from datetime import datetime
from ..utils import ProgressTracker, print_sync_start, create_progress_bar, update_last_synced

@click.group()
def series():
    """Series management commands"""
    pass

@series.command()
@click.option('--days', default=30, help='Sync series not updated in this many days')
@click.option('--limit', default=None, type=int, help='Limit number of series to sync')
@click.option('--source', default=None, help='Only sync series with books from this source (e.g. library)')
@click.option('--goodreads-id', default=None, help='Sync a specific series by Goodreads ID')
@click.option('--scrape/--no-scrape', default=False, help='Whether to scrape live or use cached data')
@click.option('--verbose/--no-verbose', default=False, help='Show detailed progress')
def sync_sa(days: int, limit: int, source: str, goodreads_id: str, scrape: bool, verbose: bool):
    """Sync unsynced series and import their books using SQLAlchemy
    
    This command uses the SQLAlchemy-based BookCreator to import books from series.
    It will create book records with proper relationships for authors, genres, and series.
    
    Example:
        cli series sync-sa --days 7  # Sync series not updated in 7 days
        cli series sync-sa --limit 10 --scrape  # Sync 10 series with fresh data
        cli series sync-sa --source library  # Only sync series with books from library
        cli series sync-sa --goodreads-id 45175  # Sync specific series by ID
    """
    # Print initial sync information
    print_sync_start(days, limit, source, goodreads_id, 'series', verbose)

    # Initialize database and session
    db = Database()
    session = Session(db.engine)
    
    try:
        # Create repositories and services
        series_repo = SeriesRepository(session)
        creator = BookCreator(session, scrape=scrape)
        series_scraper = SeriesScraper(scrape=scrape)
        
        # Initialize progress tracker
        tracker = ProgressTracker(verbose)
        
        # Get series to sync
        if goodreads_id:
            # Get or create the specific series
            series = series_repo.get_by_goodreads_id(goodreads_id)
            if not series:
                # Try to get series data to create new series
                series_data = series_scraper.scrape_series(goodreads_id)
                if series_data:
                    series = Series(
                        goodreads_id=goodreads_id,
                        title=series_data.get('title')
                    )
                    session.add(series)
                    session.commit()
                else:
                    click.echo(click.style(f"\nFailed to find or create series with ID: {goodreads_id}", fg='red'))
                    return
            series_to_sync = [series]
        else:
            # Get series that need updating
            series_to_sync = series_repo.get_series_needing_sync(days, limit, source)
        
        if verbose:
            click.echo(click.style(f"\nFound {len(series_to_sync)} series to sync", fg='blue'))
        
        # Process each series
        with create_progress_bar(series_to_sync, verbose, 'Processing series', 
                               lambda s: s.title) as series_iter:
            for series in series_iter:
                try:
                    # Get series data
                    series_data = series_scraper.scrape_series(series.goodreads_id)
                    if not series_data:
                        tracker.add_skipped(series.title, series.goodreads_id,
                                         "Failed to scrape series data", 'red')
                        continue
                    
                    # Process each book in the series
                    for book_data in series_data['books']:
                        try:
                            # Create the book
                            book = creator.create_book_from_goodreads(book_data['goodreads_id'], source='series')
                            if book:
                                tracker.increment_imported()
                            else:
                                tracker.add_skipped(book_data['title'], book_data['goodreads_id'],
                                                "Book already exists or was previously scraped")
                        except Exception as e:
                            tracker.add_skipped(book_data['title'], book_data['goodreads_id'],
                                            f"Error: {str(e)}", 'red')

                    # Update series last_synced_at
                    update_last_synced(series, session)
                    tracker.increment_processed()
                    
                except Exception as e:
                    tracker.add_skipped(series.title, series.goodreads_id,
                                    f"Error: {str(e)}", 'red')
        
        # Print results
        tracker.print_results('series')
                      
    except Exception as e:
        click.echo("\n" + click.style(f"Error during sync: {str(e)}", fg='red'), err=True)
        raise
    finally:
        session.close()

@series.command()
@click.option('--force/--no-force', default=False, help='Skip confirmation prompt')
@click.option('--verbose/--no-verbose', default=False, help='Show detailed progress')
def reset_sync(force: bool, verbose: bool):
    """Reset the sync date for all series
    
    This will set last_synced_at to NULL for all series, causing them to be
    picked up by the next sync operation.
    
    Example:
        cli series reset-sync  # Reset with confirmation
        cli series reset-sync --force  # Reset without confirmation
    """
    # Initialize database and session
    db = Database()
    session = Session(db.engine)
    
    try:
        # Get count of series to reset - include both non-null and empty string values
        count = session.query(Series).filter(
            (Series.last_synced_at.isnot(None)) | 
            (Series.last_synced_at == '')
        ).count()
        
        if count == 0:
            click.echo(click.style("\nNo series found with sync dates to reset", fg='yellow'))
            return
            
        # Show what will be reset
        click.echo("\n" + click.style(f"This will reset the sync date for {count} series", fg='yellow'))
        
        # Confirm unless force flag is used
        if not force:
            click.confirm("\nAre you sure you want to reset these sync dates?", abort=True)
        
        # Reset all sync dates in a single update
        session.query(Series).filter(
            (Series.last_synced_at.isnot(None)) | 
            (Series.last_synced_at == '')
        ).update({Series.last_synced_at: None}, synchronize_session=False)
        
        # Commit the changes
        session.commit()
        
        # Print results
        click.echo("\n" + click.style("Results:", fg='blue'))
        click.echo(click.style("Reset: ", fg='blue') + 
                  click.style(str(count), fg='green') + 
                  click.style(" series", fg='blue'))
                      
    except Exception as e:
        session.rollback()
        click.echo("\n" + click.style(f"Error during reset: {str(e)}", fg='red'), err=True)
        raise
    finally:
        session.close()
