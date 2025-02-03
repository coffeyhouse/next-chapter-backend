import click
from core.database import GoodreadsDB

@click.group()
def series():
    """Series management commands"""
    pass

@series.command()
@click.option('--db-path', '--db', default="books.db", help='Path to books database')
@click.option('--days', default=30, help='Sync series not updated in this many days')
@click.option('--limit', default=None, type=int, help='Limit number of series to sync')
def sync(db_path: str, days: int, limit: int):
    """Sync unsynced series and import their books"""
    click.echo(f"\nSyncing series not updated in {days} days")
    if limit:
        click.echo(f"Limited to {limit} series")
    
    db = GoodreadsDB(db_path)
    processed, imported = db.sync_series(days, limit)
    
    click.echo(f"\nProcessed {processed} series")
    click.echo(f"Imported {imported} new books")
