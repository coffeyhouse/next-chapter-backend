# backend/cli/main.py
import click
from typing import Optional
from .commands import AuthorCommand, BookCommand

@click.group()
def cli():
    """Goodreads Scraper CLI"""
    pass

@cli.command()
@click.option('--db-path', default="books.db", help='Path to SQLite database')
@click.option('--limit', default=None, type=int, help='Limit number of books')
@click.option('--unsynced', is_flag=True, help='Only process unsynced books')
@click.option('--scrape/--no-scrape', default=False, help='Enable/disable scraping')
def update_books(db_path: str, limit: Optional[int], unsynced: bool, scrape: bool):
    """Update book information from Goodreads"""
    command = BookCommand(db_path, scrape)
    command.update_books(unsynced_only=unsynced, limit=limit)

@cli.command()
@click.argument('book_id')
@click.option('--db-path', default="books.db", help='Path to SQLite database')
@click.option('--scrape/--no-scrape', default=False, help='Enable/disable scraping')
def update_book(book_id: str, db_path: str, scrape: bool):
    """Update a specific book by ID"""
    command = BookCommand(db_path, scrape)
    if command.update_book(book_id):
        click.echo("Successfully updated book")
    else:
        click.echo("Failed to update book")

@cli.command()
@click.option('--db-path', default="books.db", help='Path to SQLite database')
@click.option('--limit', default=None, type=int, help='Limit number of authors')
@click.option('--scrape/--no-scrape', default=False, help='Enable/disable scraping')
def update_authors(db_path: str, limit: Optional[int], scrape: bool):
    """Update author information from Goodreads"""
    command = AuthorCommand(db_path, scrape)
    
    # Debug: Check DB connection and author query
    click.echo(f"Using database: {db_path}")
    
    # Get raw query results
    sql = """
        SELECT * FROM authors 
        WHERE last_synced_at IS NULL 
        ORDER BY name
    """
    if limit:
        sql += f" LIMIT {limit}"
        
    results = command.db.execute_query(sql)
    click.echo(f"\nFound {len(results)} authors in query")
    
    if results:
        click.echo("\nFirst few authors:")
        for author in results[:3]:
            click.echo(f"- {author['name']} (ID: {author['goodreads_id']}, synced: {author['last_synced_at']})")
    
    # Continue with normal processing
    command.update_authors(limit)

if __name__ == '__main__':
    cli()