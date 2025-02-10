# core/cli/commands/library.py
import click
from core.database import GoodreadsDB
from sqlalchemy.orm import Session
from core.sa.database import Database
from core.resolvers.book_creator import BookCreator
from core.resolvers.book_resolver import BookResolver
from core.sa.models import Book, Author, Genre, Series, BookAuthor, BookGenre, BookSeries, Library, BookScraped
import sqlite3
from ..utils import ProgressTracker, print_sync_start, create_progress_bar, update_last_synced

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
@click.option('--calibre-path', default="C:/Users/warre/Calibre Library/metadata.db", required=True, help='Path to Calibre metadata.db')
@click.option('--limit', default=None, type=int, help='Limit number of books')
@click.option('--scrape/--no-scrape', default=False, help='Whether to scrape live or use cached data')
@click.option('--verbose/--no-verbose', default=False, help='Show detailed progress')
def import_calibre_sa(calibre_path: str, limit: int, scrape: bool, verbose: bool):
    """Import books from Calibre library using SQLAlchemy
    
    This command uses the SQLAlchemy-based BookCreator to import books from Calibre.
    It will create book records with proper relationships for authors, genres, and series.
    
    Example:
        cli library import-calibre-sa --calibre-path "path/to/metadata.db"
        cli library import-calibre-sa --limit 10 --scrape  # Import 10 books with fresh data
    """
    # Print initial sync information
    if verbose:
        click.echo(click.style("\nImporting from Calibre: ", fg='blue') + 
                  click.style(calibre_path, fg='cyan'))
    
    # Initialize database and session
    db = Database()
    session = Session(db.engine)
    
    try:
        # Create book creator
        creator = BookCreator(session, scrape=scrape)
        
        # Initialize progress tracker
        tracker = ProgressTracker(verbose)
        
        # Get books from Calibre database
        with sqlite3.connect(calibre_path) as calibre_conn:
            query = """
                SELECT 
                    books.id AS calibre_id,
                    books.title,
                    gr.val AS goodreads_id,
                    isbn.val AS isbn
                FROM books
                LEFT JOIN identifiers gr 
                    ON gr.book = books.id 
                    AND gr.type = 'goodreads'
                LEFT JOIN identifiers isbn
                    ON isbn.book = books.id 
                    AND isbn.type = 'isbn'
                WHERE gr.val IS NOT NULL
            """
            
            cursor = calibre_conn.execute(query)
            calibre_books = cursor.fetchall()
            
            if verbose:
                click.echo(click.style(f"\nFound {len(calibre_books)} total books in Calibre", fg='blue'))
                if len(calibre_books) > 0:
                    click.echo(click.style("First book:", fg='blue'))
                    click.echo(click.style(f"  - Title: {calibre_books[0][1]}", fg='cyan'))
                    click.echo(click.style(f"  - Goodreads ID: {calibre_books[0][2]}", fg='cyan'))
                    click.echo(click.style(f"  - ISBN: {calibre_books[0][3]}", fg='cyan'))
            
            if limit:
                calibre_books = calibre_books[:limit]
            
            # Process each book
            with create_progress_bar(calibre_books, verbose, 'Processing books', 
                                   lambda b: b[1]) as books_iter:
                for book in books_iter:
                    calibre_data = {
                        'calibre_id': book[0],
                        'title': book[1],
                        'goodreads_id': book[2],
                        'isbn': book[3]
                    }
                    
                    try:
                        # Try to create the book
                        book_obj = creator.create_book_from_goodreads(calibre_data['goodreads_id'], source='library')
                        if book_obj:
                            # Create library entry
                            library_entry = Library(
                                title=calibre_data['title'],
                                calibre_id=calibre_data['calibre_id'],
                                goodreads_id=calibre_data['goodreads_id'],
                                work_id=book_obj.work_id,
                                isbn=calibre_data['isbn']
                            )
                            session.add(library_entry)
                            session.commit()
                            tracker.increment_imported()
                        else:
                            tracker.add_skipped(calibre_data['title'], calibre_data['goodreads_id'],
                                           "Book already exists or was previously scraped")
                    except Exception as e:
                        tracker.add_skipped(calibre_data['title'], calibre_data['goodreads_id'],
                                       f"Error: {str(e)}", 'red')
                    
                    tracker.increment_processed()
            
            # Print results
            tracker.print_results('books')
                      
    except Exception as e:
        click.echo("\n" + click.style(f"Error during import: {str(e)}", fg='red'), err=True)
        raise
    finally:
        session.close()

@library.command()
@click.option('--db-path', '--db', default="books.db", help='Path to books database')
def stats(db_path: str):
    """Show library statistics"""
    db = GoodreadsDB(db_path)
    stats = db.get_stats()
    
    click.echo("\nLibrary Statistics:")
    for table, count in stats.items():
        click.echo(f"{table}: {count} records")

@library.command()
@click.argument('goodreads_id')
@click.option('--db-path', '--db', default="books.db", help='Path to books database')
@click.option('--force/--no-force', default=False, help='Skip confirmation prompt')
def delete(goodreads_id: str, db_path: str, force: bool):
    """Delete a book and its relationships from the database"""
    db = GoodreadsDB(db_path)
    
    # Get book details first
    book = db.get_by_id('book', goodreads_id, id_field='goodreads_id')
    if not book:
        click.echo(click.style(f"\nNo book found with ID: {goodreads_id}", fg='red'))
        return
        
    # Show confirmation unless force flag is used
    if not force:
        click.confirm(f"\nAre you sure you want to delete '{book['title']}'?", abort=True)
    
    if db.delete_book(goodreads_id):
        click.echo(click.style(f"\nSuccessfully deleted '{book['title']}'", fg='green'))
    else:
        click.echo(click.style("\nFailed to delete book", fg='red'))

@library.command()
@click.option('--force/--no-force', default=False, help='Skip confirmation prompts')
def empty_db(force: bool):
    """Empty the database of all records
    
    This will delete ALL records from ALL tables. Use with caution.
    Requires confirmation unless --force is used.
    
    Example:
        cli library empty-db  # Will prompt for confirmation
        cli library empty-db --force  # No confirmation prompt
    """
    db = Database()
    session = Session(db.engine)
    
    try:
        # Get counts before deletion
        counts = {
            'library': session.query(Library).count(),
            'books': session.query(Book).count(),
            'authors': session.query(Author).count(),
            'genres': session.query(Genre).count(),
            'series': session.query(Series).count(),
            'book_authors': session.query(BookAuthor).count(),
            'book_genres': session.query(BookGenre).count(),
            'book_series': session.query(BookSeries).count(),
            'book_scraped': session.query(BookScraped).count()
        }
        
        total_records = sum(counts.values())
        
        if total_records == 0:
            click.echo("Database is already empty.")
            return
            
        # Show what will be deleted
        click.echo("\nThis will delete:")
        for table, count in counts.items():
            click.echo(f"  - {count} records from {table}")
        click.echo(f"\nTotal: {total_records} records")
        
        # Confirm unless force flag is used
        if not force:
            click.confirm("\nAre you sure you want to delete ALL records?", abort=True)
            click.confirm("Are you REALLY sure? This cannot be undone!", abort=True)
        
        # Delete in correct order to avoid foreign key constraints
        click.echo("\nDeleting records...")
        
        with click.progressbar(length=9, label='Emptying database') as bar:
            session.query(BookAuthor).delete()
            bar.update(1)            

            session.query(BookGenre).delete()
            bar.update(1)
            
            session.query(BookSeries).delete()
            bar.update(1)
            
            session.query(Library).delete()
            bar.update(1)
            
            session.query(Book).delete()
            bar.update(1)
            
            session.query(Author).delete()
            bar.update(1)
            
            session.query(Genre).delete()
            bar.update(1)
            
            session.query(Series).delete()
            bar.update(1)
            
            session.query(BookScraped).delete()
            bar.update(1)
        
        session.commit()
        click.echo(click.style("\nSuccessfully emptied database", fg='green'))
        
    except Exception as e:
        session.rollback()
        click.echo(click.style(f"\nError emptying database: {str(e)}", fg='red'))
        raise
    finally:
        session.close()

@library.command()
@click.argument('source')
@click.option('--force/--no-force', default=False, help='Skip confirmation prompt')
@click.option('--verbose/--no-verbose', default=False, help='Show detailed progress')
def delete_by_source(source: str, force: bool, verbose: bool):
    """Delete all books from a specific source
    
    This command will delete all books and their relationships that came from the specified source.
    Common sources are: 'library', 'series', 'goodreads'
    
    Example:
        cli library delete-by-source series  # Delete all books from series
        cli library delete-by-source library --force  # Delete library books without confirmation
    """
    # Initialize database and session
    db = Database()
    session = Session(db.engine)
    
    try:
        # Get count of books to delete
        count = session.query(Book).filter(Book.source == source).count()
        
        if count == 0:
            click.echo(click.style(f"\nNo books found with source: {source}", fg='yellow'))
            return
            
        # Show what will be deleted
        click.echo("\n" + click.style(f"This will delete {count} books with source '{source}'", fg='yellow'))
        
        # Confirm unless force flag is used
        if not force:
            click.confirm("\nAre you sure you want to delete these books?", abort=True)
            click.confirm("Are you REALLY sure? This cannot be undone!", abort=True)
        
        # Initialize progress tracker
        tracker = ProgressTracker(verbose)
        
        # Get books to delete
        books = session.query(Book).filter(Book.source == source).all()
        
        # Process each book
        with create_progress_bar(books, verbose, 'Deleting books', 
                               lambda b: b.title) as books_iter:
            for book in books_iter:
                try:
                    # Delete relationships first
                    session.query(BookAuthor).filter_by(work_id=book.work_id).delete()
                    session.query(BookGenre).filter_by(work_id=book.work_id).delete()
                    session.query(BookSeries).filter_by(work_id=book.work_id).delete()
                    session.query(Library).filter_by(work_id=book.work_id).delete()
                    session.query(BookScraped).filter_by(work_id=book.work_id).delete()
                    
                    # Delete the book
                    session.delete(book)
                    session.commit()
                    tracker.increment_processed()
                    
                except Exception as e:
                    tracker.add_skipped(book.title, book.goodreads_id,
                                   f"Error: {str(e)}", 'red')
                    session.rollback()
        
        # Print results
        tracker.print_results('books')
                      
    except Exception as e:
        click.echo("\n" + click.style(f"Error during deletion: {str(e)}", fg='red'), err=True)
        raise
    finally:
        session.close()