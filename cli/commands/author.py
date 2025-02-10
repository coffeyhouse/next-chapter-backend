import click
from core.database import GoodreadsDB
from sqlalchemy.orm import Session
from core.sa.database import Database
from core.resolvers.book_creator import BookCreator
from core.scrapers.author_scraper import AuthorScraper
from core.scrapers.author_books_scraper import AuthorBooksScraper
from core.sa.repositories.author import AuthorRepository
from core.sa.models import Author
from datetime import datetime, UTC

@click.group()
def author():
    """Author management commands"""
    pass

@author.command()
@click.option('--db-path', '--db', default="books.db", help='Path to books database')
@click.option('--days', default=30, help='Sync authors not updated in this many days')
@click.option('--limit', default=None, type=int, help='Limit number of authors to sync')
@click.option('--source', default=None, help='Only sync authors with books from this source (e.g. library)')
def sync(db_path: str, days: int, limit: int, source: str):
    """Sync unsynced authors and import their books"""
    click.echo(f"\nSyncing authors not updated in {days} days")
    if limit:
        click.echo(f"Limited to {limit} authors")
    if source:
        click.echo(f"Only processing authors with {source} books")
    
    db = GoodreadsDB(db_path)
    processed, imported = db.sync_authors(days, limit, source)
    
    click.echo(f"\nProcessed {processed} authors")
    click.echo(f"Imported {imported} new books")

@author.command()
@click.option('--days', default=30, help='Sync authors not updated in this many days')
@click.option('--limit', default=None, type=int, help='Limit number of authors to sync')
@click.option('--source', default=None, help='Only sync authors with books from this source (e.g. library)')
@click.option('--scrape/--no-scrape', default=False, help='Whether to scrape live or use cached data')
@click.option('--verbose/--no-verbose', default=False, help='Show detailed progress')
def sync_sa(days: int, limit: int, source: str, scrape: bool, verbose: bool):
    """Sync unsynced authors and import their books using SQLAlchemy
    
    This command uses the SQLAlchemy-based BookCreator to import books from authors.
    It will create book records with proper relationships for authors, genres, and series.
    
    Example:
        cli author sync-sa --days 7  # Sync authors not updated in 7 days
        cli author sync-sa --limit 10 --scrape  # Sync 10 authors with fresh data
    """
    if verbose:
        click.echo(click.style("\nSyncing authors not updated in ", fg='blue') + 
                  click.style(str(days), fg='cyan') + 
                  click.style(" days", fg='blue'))
        if limit:
            click.echo(click.style("Limited to ", fg='blue') + 
                      click.style(str(limit), fg='cyan') + 
                      click.style(" authors", fg='blue'))
        if source:
            click.echo(click.style("Only processing authors with ", fg='blue') + 
                      click.style(source, fg='cyan') + 
                      click.style(" books", fg='blue'))

    # Initialize database and session
    db = Database()
    session = Session(db.engine)
    
    try:
        # Create repositories and services
        author_repo = AuthorRepository(session)
        creator = BookCreator(session, scrape=scrape)
        author_scraper = AuthorScraper(scrape=scrape)
        books_scraper = AuthorBooksScraper(scrape=scrape)
        
        # Get authors that need updating
        authors_to_sync = author_repo.get_unsynced_authors(days)
        if limit:
            authors_to_sync = authors_to_sync[:limit]
        
        if verbose:
            click.echo(click.style(f"\nFound {len(authors_to_sync)} authors to sync", fg='blue'))
        
        processed = 0
        imported = 0
        skipped = []
        
        # Process each author
        with click.progressbar(
            authors_to_sync,
            label=click.style('Processing authors', fg='blue'),
            item_show_func=lambda a: click.style(a.name, fg='cyan') if a and verbose else None,
            show_eta=True,
            show_percent=True,
            width=50
        ) as author_iter:
            for author in author_iter:
                try:
                    # Get author data
                    author_data = author_scraper.scrape_author(author.goodreads_id)
                    if not author_data:
                        skipped.append({
                            'name': author.name,
                            'goodreads_id': author.goodreads_id,
                            'reason': "Failed to scrape author data",
                            'color': 'red'
                        })
                        continue

                    # Get author's books
                    books_data = books_scraper.scrape_author_books(author.goodreads_id)
                    if not books_data:
                        skipped.append({
                            'name': author.name,
                            'goodreads_id': author.goodreads_id,
                            'reason': "Failed to scrape author's books",
                            'color': 'red'
                        })
                        continue

                    # Process each book
                    for book_data in books_data['books']:
                        try:
                            # First get the full book data to check author role
                            book_details = creator.resolver.resolve_book(book_data['goodreads_id'])
                            if not book_details:
                                skipped.append({
                                    'name': book_data['title'],
                                    'goodreads_id': book_data['goodreads_id'],
                                    'reason': "Failed to get book details",
                                    'color': 'red'
                                })
                                continue

                            # Check if this author is listed as 'Author' for this book
                            is_primary_author = False
                            author_role = None
                            for book_author in book_details.get('authors', []):
                                if book_author.get('goodreads_id') == author.goodreads_id:
                                    author_role = book_author.get('role', '')
                                    if author_role.lower() == 'author':
                                        is_primary_author = True
                                    break

                            if not is_primary_author:
                                if verbose:
                                    skipped.append({
                                        'name': book_data['title'],
                                        'goodreads_id': book_data['goodreads_id'],
                                        'reason': f"Author role is '{author_role or 'Unknown'}' (not primary Author)",
                                        'color': 'yellow'
                                    })
                                continue

                            # Create the book since author is primary
                            book = creator.create_book_from_goodreads(book_data['goodreads_id'], source='author')
                            if book:
                                imported += 1
                            elif verbose:
                                skipped.append({
                                    'name': book_data['title'],
                                    'goodreads_id': book_data['goodreads_id'],
                                    'reason': "Book already exists or was previously scraped",
                                    'color': 'yellow'
                                })
                        except Exception as e:
                            skipped.append({
                                'name': book_data['title'],
                                'goodreads_id': book_data['goodreads_id'],
                                'reason': f"Error: {str(e)}",
                                'color': 'red'
                            })

                    # Update author last_synced_at
                    author.last_synced_at = datetime.now(UTC)
                    session.commit()
                    
                    processed += 1
                    
                except Exception as e:
                    skipped.append({
                        'name': author.name,
                        'goodreads_id': author.goodreads_id,
                        'reason': f"Error: {str(e)}",
                        'color': 'red'
                    })
        
        # Print results
        click.echo("\n" + click.style("Results:", fg='blue'))
        click.echo(click.style("Processed: ", fg='blue') + 
                  click.style(str(processed), fg='cyan') + 
                  click.style(" authors", fg='blue'))
        click.echo(click.style("Imported: ", fg='blue') + 
                  click.style(str(imported), fg='green') + 
                  click.style(" books", fg='blue'))
        
        if skipped and verbose:
            click.echo("\n" + click.style("Skipped items:", fg='yellow'))
            for skip_info in skipped:
                click.echo("\n" + click.style(f"Name: {skip_info['name']}", fg=skip_info['color']))
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

if __name__ == '__main__':
    author()