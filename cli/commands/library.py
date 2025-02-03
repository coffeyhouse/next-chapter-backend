# core/cli/commands/library.py
import click
from core.database import GoodreadsDB

@click.group()
def library():
    """Library management commands"""
    pass

@library.command()
@click.option('--db-path', '--db', default="books.db", help='Path to books database')
@click.option('--calibre-path', default="C:/Users/warre/Calibre Library/metadata.db", required=True, help='Path to Calibre metadata.db')
@click.option('--limit', default=None, type=int, help='Limit number of books')
def import_calibre(db_path: str, calibre_path: str, limit: int):
    """Import books from Calibre library"""
    click.echo(f"\nImporting from Calibre: {calibre_path}")
    
    db = GoodreadsDB(db_path)
    total, imported = db.import_calibre_books(calibre_path, limit)
    
    click.echo(f"\nProcessed {total} books")
    click.echo(f"Successfully imported {imported} books")

@library.command()
@click.option('--db-path', '--db', default="books.db", help='Path to books database')
def stats(db_path: str):
    """Show library statistics"""
    db = GoodreadsDB(db_path)
    stats = db.get_stats()
    
    click.echo("\nLibrary Statistics:")
    for table, count in stats.items():
        click.echo(f"{table}: {count} records")