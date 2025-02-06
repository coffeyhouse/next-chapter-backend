# cli/commands/similar.py

import click
from core.database import GoodreadsDB

@click.group()
def similar():
    """Similar books management commands"""
    pass

@similar.command()
@click.option('--db-path', '--db', default="books.db", help='Path to books database')
@click.option('--limit', default=None, type=int, help='Limit number of books to process')
@click.option('--source', default=None, help='Only sync similar books for books from this source (e.g. library)')
def sync(db_path: str, limit: int, source: str):
    """Sync similar books relationships"""
    click.echo("\nSyncing similar books")
    if limit:
        click.echo(f"Limited to {limit} books")
    if source:
        click.echo(f"Only processing books with source: {source}")
    
    db = GoodreadsDB(db_path)
    processed, imported = db.sync_similar(source, limit)
    
    click.echo(f"\nProcessed {processed} books")
    click.echo(f"Imported {imported} similar book relationships")

if __name__ == '__main__':
    similar()
