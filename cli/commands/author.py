import click
from core.database import GoodreadsDB
from core.scrapers.author_scraper import AuthorScraper
from core.scrapers.author_books_scraper import AuthorBooksScraper

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