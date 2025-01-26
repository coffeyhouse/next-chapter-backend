#!/usr/bin/env python
import click
from datetime import datetime
from backend.scrapers.book import scrape_book
from backend.scrapers.author import scrape_author
from backend.scrapers.author_books import scrape_author_books
from backend.scrapers.series import scrape_series
from backend.scrapers.similar import scrape_similar
from backend.scrapers.editions import scrape_editions
from backend.calibre.library_import import process_calibre_books
from backend.utils.data_transformer import (
    transform_book_data,
    transform_author_data,
    transform_author_books_data,
    transform_editions_data,
    transform_series_data,
    transform_similar_data,
    print_transformed_data
)

# Ensure backend module can be imported
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

@click.group()
def cli():
    """Goodreads Scraper CLI"""
    pass

@cli.command()
@click.option('--db-path', default="C:/Users/warre/Calibre Library/metadata.db",
              help='Path to Calibre metadata.db file')
@click.option('--limit', default=None, type=int,
              help='Limit the number of books to process')
def calibre(db_path, limit):
    """Process books from Calibre library"""
    try:
        tables = process_calibre_books(db_path, limit)
        if tables['book']:
            print_transformed_data(tables)
        else:
            click.echo("No books found in Calibre database")
    except Exception as e:
        click.echo(f"Error processing Calibre database: {str(e)}")

@cli.command()
@click.argument('book_id')
def book(book_id):
    """Scrape a book by its ID"""
    book_info = scrape_book(book_id)
    if book_info:
        tables = transform_book_data(book_info)
        print_transformed_data(tables)
    else:
        click.echo(f"Failed to retrieve book with ID: {book_id}")

@cli.command()
@click.argument('author_id')
def author(author_id):
    """Scrape an author by their ID"""
    author_info = scrape_author(author_id)
    if author_info:
        tables = transform_author_data(author_info)
        print_transformed_data(tables)
    else:
        click.echo(f"Failed to retrieve author with ID: {author_id}")

@cli.command()
@click.argument('author_id')
def author_books(author_id):
    """Scrape all books by an author"""
    result = scrape_author_books(author_id)
    if result:
        tables = transform_author_books_data(result)
        print_transformed_data(tables)
    else:
        click.echo(f"Failed to retrieve books for author ID: {author_id}")

@cli.command()
@click.argument('series_id')
def series(series_id):
    """Scrape a series by its ID"""
    series_info = scrape_series(series_id)
    if series_info:
        tables = transform_series_data(series_info)
        print_transformed_data(tables)
    else:
        click.echo(f"Failed to retrieve series with ID: {series_id}")

@cli.command()
@click.argument('book_id')
def similar(book_id):
    """Find similar books"""
    result = scrape_similar(book_id)
    if result:
        tables = transform_similar_data(result)
        print_transformed_data(tables)
    else:
        click.echo(f"Failed to retrieve similar books for ID: {book_id}")

@cli.command()
@click.argument('work_id')
def editions(work_id):
    """Scrape all editions of a book"""
    first_edition, all_editions = scrape_editions(work_id)
    if all_editions:
        tables = transform_editions_data((first_edition, all_editions))
        print_transformed_data(tables)
    else:
        click.echo(f"Failed to retrieve editions for work ID: {work_id}")
        
@cli.command()
@click.argument('book_id')
@click.argument('user_id')
@click.option('--status', type=click.Choice(['reading', 'read']), required=True)
@click.option('--started', type=click.DateTime(), help='Start date (YYYY-MM-DD)')
@click.option('--finished', type=click.DateTime(), help='Finish date (YYYY-MM-DD)')
def reading_status(book_id, user_id, status, started, finished):
    """Update reading status for a book"""
    now = datetime.now().isoformat()
    
    tables = {
        'book_user': [{
            'book_id': book_id,
            'user_id': user_id,
            'status': status,
            'source': 'manual',
            'started_at': started.isoformat() if started else None,
            'finished_at': finished.isoformat() if finished else None,
            'created_at': now,
            'updated_at': now
        }]
    }
    print_transformed_data(tables)

if __name__ == '__main__':
    cli()