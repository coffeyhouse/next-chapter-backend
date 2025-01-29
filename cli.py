#!/usr/bin/env python
import click
import sqlite3
import re
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
    """Scrape a specific series"""
    result = scrape_series(series_id)
    if result:
        tables = transform_series_data(result)
        print_transformed_data(tables)
        
        # Insert into database
        db = DatabaseOperations('books.db')
        if db.insert_transformed_data(tables):
            click.echo(f"Successfully added series: {result['name']}")
        else:
            click.echo("Failed to add series to database")
    else:
        click.echo(f"Failed to retrieve series ID: {series_id}")

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
@click.option('--source', type=click.Choice(['library', 'series', 'author', 'editions']), 
              default='library', help='Source of books to update')
def update_library(db_path, limit, source):
    """Update books with data from Goodreads based on source"""
    try:
        # Connect to database
        db = DatabaseOperations(db_path)
        
        # Query based on source
        with sqlite3.connect(db_path) as conn:
            if source == 'library':
                query = """
                    SELECT b.goodreads_id, b.title, b.calibre_id
                    FROM books b 
                    WHERE b.source = 'library' 
                    AND (b.last_synced_at IS NULL OR b.last_synced_at = '')
                    ORDER BY b.goodreads_id
                """
            elif source == 'series':
                query = """
                    SELECT b.goodreads_id, b.title, NULL as calibre_id
                    FROM books b 
                    WHERE b.source = 'series'
                    AND (b.last_synced_at IS NULL OR b.last_synced_at = '')
                    ORDER BY b.goodreads_id
                """
            elif source == 'editions':
                query = """
                    SELECT b.goodreads_id, b.title, NULL as calibre_id
                    FROM books b 
                    WHERE b.source = 'editions'
                    AND (b.last_synced_at IS NULL OR b.last_synced_at = '')
                    ORDER BY b.goodreads_id
                """
            else:  # author
                query = """
                    SELECT b.goodreads_id, b.title, NULL as calibre_id
                    FROM books b 
                    WHERE b.source = 'author'
                    AND (b.last_synced_at IS NULL OR b.last_synced_at = '')
                    ORDER BY b.goodreads_id
                """
            
            if limit:
                query += f" LIMIT {limit}"
                
            cursor = conn.execute(query)
            books = cursor.fetchall()
            
        if not books:
            click.echo(f"No unsynced {source} books found")
            return
            
        click.echo(f"Found {len(books)} unsynced {source} books")
        
        # Process each book
        success_count = 0
        for i, (goodreads_id, title, calibre_id) in enumerate(books, 1):
            click.echo(f"\nProcessing {i}/{len(books)}: {title} ({goodreads_id})")
            
            try:
                # Scrape book data
                book_info = scrape_book(goodreads_id)
                if book_info:
                    # Preserve source and calibre_id if present
                    book_info['source'] = source
                    if calibre_id:
                        book_info['calibre_id'] = calibre_id
                    
                    # Transform data
                    tables = transform_book_data(book_info)
                    
                    # Ensure books table has the calibre_id if present
                    if calibre_id and 'book' in tables and tables['book']:
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
                
        click.echo(f"\nCompleted processing {len(books)} books")
        click.echo(f"Successfully updated {success_count} books")
        
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@cli.command()
@click.option('--db-path', default="books.db",
              help='Path to SQLite database')
@click.option('--limit', default=None, type=int,
              help='Limit the number of books to process')
def scrape_all_editions(db_path, limit):
    """Scrape editions for non-English books"""
    try:
        # Connect to database
        db = DatabaseOperations(db_path)
        
        # Query for non-English books with similar_books_id
        with sqlite3.connect(db_path) as conn:
            query = """
                SELECT b.goodreads_id, b.title, b.similar_books_id
                FROM books b 
                WHERE b.similar_books_id IS NOT NULL
                AND b.similar_books_id != ''
                AND (b.language != 'English' OR b.language IS NULL)
                ORDER BY b.goodreads_id
            """
            
            if limit:
                query += f" LIMIT {limit}"
                
            cursor = conn.execute(query)
            books = cursor.fetchall()
            
            # Get all library books for reference
            cursor = conn.execute("""
                SELECT goodreads_id 
                FROM books 
                WHERE source = 'library'
            """)
            library_books = {row[0] for row in cursor.fetchall()}
            
        if not books:
            click.echo("No non-English books found")
            return
            
        click.echo(f"Found {len(books)} non-English books")
        
        # Process each book
        success_count = 0
        for i, (goodreads_id, title, similar_books_id) in enumerate(books, 1):
            click.echo(f"\nProcessing {i}/{len(books)}: {title}")
            
            try:
                # Scrape editions data
                editions_data = scrape_editions(similar_books_id)
                if editions_data:
                    # Transform data
                    tables = transform_editions_data(editions_data, library_books)
                    
                    # Insert into database
                    if db.insert_transformed_data(tables):
                        click.echo(f"Successfully updated editions for: {title}")
                        success_count += 1
                    else:
                        click.echo(f"Failed to update editions for: {title}")
                else:
                    click.echo(f"Failed to scrape editions for: {title}")
            except Exception as e:
                click.echo(f"Error processing book {title}: {str(e)}")
                continue
                
        click.echo(f"\nCompleted processing {len(books)} books")
        click.echo(f"Successfully updated {success_count} books")
        
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@cli.command()
@click.option('--db-path', default="books.db",
              help='Path to SQLite database')
@click.option('--limit', default=None, type=int,
              help='Limit the number of series to process')
def scrape_all_series(db_path, limit):
    """Scrape all series"""
    try:
        # Connect to database
        db = DatabaseOperations(db_path)
        
        # Get all library books for reference
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("""
                SELECT goodreads_id 
                FROM books
            """)
            library_books = {row[0] for row in cursor.fetchall()}
            
        # Query for books with series IDs
        with sqlite3.connect(db_path) as conn:
            query = """
                SELECT DISTINCT bs.series_id, s.title
                FROM book_series bs
                JOIN series s ON bs.series_id = s.goodreads_id
                WHERE s.last_synced_at IS NULL
                ORDER BY bs.series_id
            """
            
            if limit:
                query += f" LIMIT {limit}"
                
            cursor = conn.execute(query)
            series_list = cursor.fetchall()
            
        if not series_list:
            click.echo("No unsynced series found")
            return
            
        click.echo(f"Found {len(series_list)} unsynced series")
        
        # Process each series
        success_count = 0
        for i, (series_id, title) in enumerate(series_list, 1):
            click.echo(f"\nProcessing {i}/{len(series_list)}: {title}")
            
            try:
                # Scrape series data
                series_info = scrape_series(series_id)
                if series_info:
                    # Transform data
                    tables = transform_series_data(series_info, library_books)
                    
                    # Insert into database
                    if db.insert_transformed_data(tables):
                        click.echo(f"Successfully updated series: {title}")
                        success_count += 1
                    else:
                        click.echo(f"Failed to update series: {title}")
                else:
                    click.echo(f"Failed to scrape series: {title}")
            except Exception as e:
                click.echo(f"Error processing series {title}: {str(e)}")
                continue
                
        click.echo(f"\nCompleted processing {len(series_list)} series")
        click.echo(f"Successfully updated {success_count} series")
        
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@cli.command()
@click.option('--db-path', default="books.db",
              help='Path to SQLite database')
@click.option('--limit', default=None, type=int,
              help='Limit the number of books to process')
def match_library_books(db_path, limit):
    """Match unmatched books to Calibre library entries by author and title"""
    try:
        # Connect to database
        db = DatabaseOperations(db_path)
        
        with sqlite3.connect(db_path) as conn:
            # Get unmatched books with authors
            query = """
                WITH book_authors AS (
                    SELECT 
                        b.goodreads_id,
                        b.title as book_title,
                        GROUP_CONCAT(a.name, '|') as author_names
                    FROM books b
                    JOIN author_books ab ON b.goodreads_id = ab.book_id
                    JOIN authors a ON ab.author_id = a.goodreads_id
                    WHERE b.calibre_id IS NULL
                    AND b.source != 'library'
                    GROUP BY b.goodreads_id
                )
                SELECT 
                    ba.goodreads_id,
                    ba.book_title,
                    ba.author_names
                FROM book_authors ba
                ORDER BY ba.book_title
            """
            
            if limit:
                query += f" LIMIT {limit}"
                
            cursor = conn.execute(query)
            unmatched_books = cursor.fetchall()
            
            # Get all library entries with authors
            library_query = """
                SELECT 
                    l.calibre_id,
                    l.title as library_title,
                    l.goodreads_id,
                    GROUP_CONCAT(a.name, '|') as author_names
                FROM library l
                JOIN books b ON l.goodreads_id = b.goodreads_id
                JOIN author_books ab ON b.goodreads_id = ab.book_id
                JOIN authors a ON ab.author_id = a.goodreads_id
                GROUP BY l.calibre_id
            """
            cursor = conn.execute(library_query)
            library_books = cursor.fetchall()
            
            if not unmatched_books:
                click.echo("No unmatched books found")
                return
                
            click.echo(f"Found {len(unmatched_books)} unmatched books")
            
            # Process each unmatched book
            matches_found = 0
            for book_id, title, authors in unmatched_books:
                click.echo(f"\nProcessing: {title}")
                
                # Clean and normalize the title
                clean_title = clean_text(title)
                author_list = [clean_text(a) for a in authors.split('|')]
                
                # Look for matches in library books
                best_match = None
                best_score = 0
                
                for lib_id, lib_title, lib_goodreads_id, lib_authors in library_books:
                    # Skip if already matched to Goodreads
                    if lib_goodreads_id:
                        continue
                        
                    clean_lib_title = clean_text(lib_title)
                    lib_author_list = [clean_text(a) for a in lib_authors.split('|')]
                    
                    # Calculate title similarity
                    title_similarity = max(
                        similar(clean_title, clean_lib_title),
                        similar(clean_title, clean_lib_title.replace(' series', '')),
                        similar(clean_title.replace(' series', ''), clean_lib_title)
                    )
                    
                    # Calculate author similarity - match any author
                    author_similarity = max(
                        max(similar(a1, a2) for a2 in lib_author_list)
                        for a1 in author_list
                    )
                    
                    # Weight title and author matches
                    score = (title_similarity * 0.6) + (author_similarity * 0.4)
                    
                    if score > 0.7 and score > best_score:  # Lowered threshold
                        best_score = score
                        best_match = (lib_id, lib_title, score)
                
                if best_match:
                    lib_id, lib_title, score = best_match
                    click.echo(f"Found match: {lib_title} (score: {score:.2f})")
                    
                    # Update the books table with calibre_id
                    update_query = """
                        UPDATE books 
                        SET calibre_id = ? 
                        WHERE goodreads_id = ?
                    """
                    conn.execute(update_query, (lib_id, book_id))
                    conn.commit()
                    
                    matches_found += 1
                else:
                    click.echo("No match found")
            
            click.echo(f"\nMatched {matches_found} books")
            
    except Exception as e:
        click.echo(f"Error: {str(e)}")

def clean_text(text):
    """Clean and normalize text for comparison"""
    # Remove common words and punctuation
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\b(the|a|an)\b', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def similar(a, b):
    """Calculate similarity ratio between two strings"""
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio()

if __name__ == '__main__':
    cli()