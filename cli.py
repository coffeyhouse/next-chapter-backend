#!/usr/bin/env python
import click
import sqlite3
from datetime import datetime
from backend.scrapers.book import scrape_book
from backend.scrapers.author import scrape_author
from backend.scrapers.author_books import scrape_author_books
from backend.scrapers.series import scrape_series
from backend.scrapers.similar import scrape_similar
from backend.scrapers.editions import scrape_editions
from backend.db.db_operations import DatabaseOperations
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
@click.option('--output-db', default="books.db",
              help='Path to output SQLite database')
def calibre(db_path, limit, output_db):
    """Process books from Calibre library"""
    try:
        tables = process_calibre_books(db_path, limit)
        if tables['book']:
            print_transformed_data(tables)
            
            # Insert into database
            db = DatabaseOperations(output_db)
            if db.insert_transformed_data(tables):
                print("\nSuccessfully inserted data into database")
                stats = db.get_stats()
                print("\nDatabase statistics:")
                for table, count in stats.items():
                    print(f"{table}: {count} records")
            else:
                click.echo("Failed to insert data into database")
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
    
@cli.command()
@click.option('--db-path', default="books.db",
              help='Path to SQLite database')
@click.option('--limit', default=None, type=int,
              help='Limit the number of books to process')
def update_library(db_path, limit):
    """Update library books with data from Goodreads"""
    try:
        # Connect to database
        db = DatabaseOperations(db_path)
        
        # Query for unsynced library books
        with sqlite3.connect(db_path) as conn:
            query = """
                SELECT b.goodreads_id, b.title, b.calibre_id
                FROM books b 
                WHERE b.source = 'library' 
                AND (b.last_synced_at IS NULL OR b.last_synced_at = '')
                ORDER BY b.goodreads_id
            """
            
            if limit:
                query += f" LIMIT {limit}"
                
            cursor = conn.execute(query)
            books = cursor.fetchall()
            
        if not books:
            click.echo("No unsynced library books found")
            return
            
        click.echo(f"Found {len(books)} unsynced library books")
        
        # Process each book
        success_count = 0
        for i, (goodreads_id, title, calibre_id) in enumerate(books, 1):
            click.echo(f"\nProcessing {i}/{len(books)}: {title} ({goodreads_id})")
            
            try:
                # Scrape book data
                book_info = scrape_book(goodreads_id)
                if book_info:
                    # Preserve library source and calibre_id
                    book_info['source'] = 'library'
                    book_info['calibre_id'] = calibre_id
                    
                    # Transform data
                    tables = transform_book_data(book_info)
                    
                    # Ensure books table has the calibre_id
                    if 'book' in tables and tables['book']:
                        tables['book'][0]['calibre_id'] = calibre_id
                    
                    # Insert into database
                    if db.insert_transformed_data(tables):
                        click.echo(f"Successfully updated book: {title}")
                        success_count += 1
                    else:
                        click.echo(f"Failed to update book: {title}")
                else:
                    click.echo(f"Failed to scrape book: {title}")
            except Exception as e:
                click.echo(f"Error processing book {title}: {str(e)}")
                continue
                
        # Print final stats
        click.echo(f"\nSuccessfully updated {success_count} out of {len(books)} books")
        stats = db.get_stats()
        click.echo("\nDatabase statistics:")
        for table, count in stats.items():
            click.echo(f"{table}: {count} records")
            
    except Exception as e:
        click.echo(f"Error updating library: {str(e)}")

if __name__ == '__main__':
    cli()