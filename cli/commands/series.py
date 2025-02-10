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

@click.group()
def series():
    """Series management commands"""
    pass

@series.command()
@click.option('--db-path', '--db', default="books.db", help='Path to books database')
@click.option('--days', default=30, help='Sync series not updated in this many days')
@click.option('--limit', default=None, type=int, help='Limit number of series to sync')
@click.option('--source', default=None, help='Only sync series with books from this source (e.g. library)')
def sync(db_path: str, days: int, limit: int, source: str):
    """Sync unsynced series and import their books"""
    click.echo(f"\nSyncing series not updated in {days} days")
    if limit:
        click.echo(f"Limited to {limit} series")
    if source:
        click.echo(f"Only processing series with {source} books")
    
    db = GoodreadsDB(db_path)
    processed, imported = db.sync_series(days, limit, source)
    
    click.echo(f"\nProcessed {processed} series")
    click.echo(f"Imported {imported} new books")

@series.command()
@click.option('--days', default=30, help='Sync series not updated in this many days')
@click.option('--limit', default=None, type=int, help='Limit number of series to sync')
@click.option('--source', default=None, help='Only sync series with books from this source (e.g. library)')
@click.option('--scrape/--no-scrape', default=False, help='Whether to scrape live or use cached data')
@click.option('--verbose/--no-verbose', default=False, help='Show detailed progress')
def sync_sa(days: int, limit: int, source: str, scrape: bool, verbose: bool):
    """Sync unsynced series and import their books using SQLAlchemy
    
    This command uses the SQLAlchemy-based BookCreator to import books from series.
    It will create book records with proper relationships for authors, genres, and series.
    
    Example:
        cli series sync-sa --days 7  # Sync series not updated in 7 days
        cli series sync-sa --limit 10 --scrape  # Sync 10 series with fresh data
        cli series sync-sa --source library  # Only sync series with books from library
    """
    if verbose:
        click.echo(click.style("\nSyncing series not updated in ", fg='blue') + 
                  click.style(str(days), fg='cyan') + 
                  click.style(" days", fg='blue'))
        if limit:
            click.echo(click.style("Limited to ", fg='blue') + 
                      click.style(str(limit), fg='cyan') + 
                      click.style(" series", fg='blue'))
        if source:
            click.echo(click.style("Only processing series with ", fg='blue') + 
                      click.style(source, fg='cyan') + 
                      click.style(" books", fg='blue'))
    
    # Initialize database and session
    db = Database()
    session = Session(db.engine)
    
    try:
        # Create repositories and services
        series_repo = SeriesRepository(session)
        creator = BookCreator(session, scrape=scrape)
        scraper = SeriesScraper(scrape=scrape)
        
        # Get series that need updating
        series_to_sync = series_repo.get_series_needing_sync(days, limit, source)
        
        if verbose:
            click.echo(click.style(f"\nFound {len(series_to_sync)} series to sync", fg='blue'))
        
        processed = 0
        imported = 0
        skipped = []
        
        # Process each series
        with click.progressbar(
            series_to_sync,
            label=click.style('Processing series', fg='blue'),
            item_show_func=lambda s: click.style(s.title, fg='cyan') if s and verbose else None,
            show_eta=True,
            show_percent=True,
            width=50
        ) as series_iter:
            for series in series_iter:
                try:
                    # Get series data
                    series_data = scraper.scrape_series(series.goodreads_id)
                    if not series_data:
                        skipped.append({
                            'title': series.title,
                            'goodreads_id': series.goodreads_id,
                            'reason': "Failed to scrape series data",
                            'color': 'red'
                        })
                        continue
                    
                    # Process each book in the series
                    for book_data in series_data['books']:
                        try:
                            # Create the book
                            book = creator.create_book_from_goodreads(book_data['goodreads_id'], source='series')
                            if book:
                                imported += 1
                            elif verbose:
                                skipped.append({
                                    'title': book_data['title'],
                                    'goodreads_id': book_data['goodreads_id'],
                                    'reason': "Book already exists or was previously scraped",
                                    'color': 'yellow'
                                })
                        except Exception as e:
                            skipped.append({
                                'title': book_data['title'],
                                'goodreads_id': book_data['goodreads_id'],
                                'reason': f"Error: {str(e)}",
                                'color': 'red'
                            })
                    
                    # Update series last_synced_at
                    series.last_synced_at = datetime.utcnow()
                    session.commit()
                    
                    processed += 1
                    
                except Exception as e:
                    skipped.append({
                        'title': series.title,
                        'goodreads_id': series.goodreads_id,
                        'reason': f"Error: {str(e)}",
                        'color': 'red'
                    })
        
        # Print results
        click.echo("\n" + click.style("Results:", fg='blue'))
        click.echo(click.style("Processed: ", fg='blue') + 
                  click.style(str(processed), fg='cyan') + 
                  click.style(" series", fg='blue'))
        click.echo(click.style("Imported: ", fg='blue') + 
                  click.style(str(imported), fg='green') + 
                  click.style(" books", fg='blue'))
        
        if skipped and verbose:
            click.echo("\n" + click.style("Skipped items:", fg='yellow'))
            for skip_info in skipped:
                click.echo("\n" + click.style(f"Title: {skip_info['title']}", fg=skip_info['color']))
                click.echo(click.style(f"Goodreads ID: {skip_info['goodreads_id']}", fg=skip_info['color']))
                click.echo(click.style(f"Reason: {skip_info['reason']}", fg=skip_info['color']))
        elif skipped:
            click.echo(click.style(f"\nSkipped {len(skipped)} items. ", fg='yellow') + 
                      click.style("Use --verbose to see details.", fg='blue'))
                      
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
