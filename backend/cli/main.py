# backend/cli/main.py
import click
from typing import Optional
from .commands import AuthorCommand

@click.group()
def cli():
    """Goodreads Scraper CLI"""
    pass

@cli.command()
@click.option('--db-path', default="books.db", help='Path to SQLite database')
@click.option('--limit', default=None, type=int, help='Limit number of authors')
@click.option('--scrape/--no-scrape', default=False, help='Enable/disable scraping')
def update_authors(db_path: str, limit: Optional[int], scrape: bool):
    """Update author information from Goodreads"""
    command = AuthorCommand(db_path, scrape)
    command.update_authors(limit)

if __name__ == '__main__':
    cli()