import click
from sqlalchemy.orm import Session
from core.sa.database import Database
from core.resolvers.book_creator import BookCreator
from core.sa.models import Book, Author, Genre, Series, BookAuthor, BookGenre, BookSeries, Library, BookScraped
from core.sa.repositories.user import UserRepository
import sqlite3
from ..utils import ProgressTracker, create_progress_bar
from typing import Dict, Any, List
from core.utils.book_sync_helper import process_book_ids

# Default Calibre database path
DEFAULT_CALIBRE_PATH = "C:/Users/warre/Calibre Library/metadata.db"

def print_reading_data(data: List[Dict[str, Any]]):
    """Print reading progress data in a readable format."""
    print("\nReading Progress Data:")
    print("-" * 80)
    for entry in data:
        print(f"\nBook: {entry['title']} (Calibre ID: {entry['calibre_id']}, Goodreads ID: {entry['goodreads_id']})")
        print("Warren:")
        print(f"  Last Read: {entry['warren_last_read'] or 'Never'}")
        print(f"  Progress: {entry['warren_read_percent']}%")
        print("Ruth:")
        print(f"  Last Read: {entry['ruth_last_read'] or 'Never'}")
        print(f"  Progress: {entry['ruth_read_percent']}%")
    print("-" * 80)

def determine_status(read_percent: float) -> str:
    """Determine reading status based on percentage."""
    if read_percent is None or read_percent == 0:
        return "want_to_read"
    elif read_percent == 100:
        return "completed"
    else:
        return "reading"

@click.group()
def library():
    """Library management commands"""
    pass

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
    if verbose:
        click.echo(click.style("\nImporting from Calibre: ", fg='blue') + 
                   click.style(calibre_path, fg='cyan'))
    
    db = Database()
    session = Session(db.engine)
    
    try:
        creator = BookCreator(session, scrape=scrape)
        tracker = ProgressTracker(verbose)
        
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
            
            with create_progress_bar(calibre_books, verbose, 'Processing books', lambda b: b[1]) as books_iter:
                for book in books_iter:
                    calibre_data = {
                        'calibre_id': book[0],
                        'title': book[1],
                        'goodreads_id': book[2],
                        'isbn': book[3]
                    }
                    
                    try:
                        # Use process_book_ids to get or create the book
                        books_created = process_book_ids(session, [calibre_data['goodreads_id']], source='library', scrape=scrape)
                        book_obj = books_created[0] if books_created else None
                        
                        if book_obj:
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
                        session.rollback()
                    
                    tracker.increment_processed()
            
            tracker.print_results('books')
                      
    except Exception as e:
        click.echo("\n" + click.style(f"Error during import: {str(e)}", fg='red'), err=True)
        raise
    finally:
        session.close()

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
            
        click.echo("\nThis will delete:")
        for table, count in counts.items():
            click.echo(f"  - {count} records from {table}")
        click.echo(f"\nTotal: {total_records} records")
        
        if not force:
            click.confirm("\nAre you sure you want to delete ALL records?", abort=True)
            click.confirm("Are you REALLY sure? This cannot be undone!", abort=True)
        
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
    db = Database()
    session = Session(db.engine)
    
    try:
        count = session.query(Book).filter(Book.source == source).count()
        
        if count == 0:
            click.echo(click.style(f"\nNo books found with source: {source}", fg='yellow'))
            return
            
        click.echo("\n" + click.style(f"This will delete {count} books with source '{source}'", fg='yellow'))
        
        if not force:
            click.confirm("\nAre you sure you want to delete these books?", abort=True)
            click.confirm("Are you REALLY sure? This cannot be undone!", abort=True)
        
        tracker = ProgressTracker(verbose)
        books = session.query(Book).filter(Book.source == source).all()
        
        with create_progress_bar(books, verbose, 'Deleting books', lambda b: b.title) as books_iter:
            for book in books_iter:
                try:
                    session.query(BookAuthor).filter_by(work_id=book.work_id).delete()
                    session.query(BookGenre).filter_by(work_id=book.work_id).delete()
                    session.query(BookSeries).filter_by(work_id=book.work_id).delete()
                    session.query(Library).filter_by(work_id=book.work_id).delete()
                    session.query(BookScraped).filter_by(work_id=book.work_id).delete()
                    
                    session.delete(book)
                    session.commit()
                    tracker.increment_processed()
                    
                except Exception as e:
                    tracker.add_skipped(book.title, book.goodreads_id,
                                        f"Error: {str(e)}", 'red')
                    session.rollback()
        
        tracker.print_results('books')
                      
    except Exception as e:
        click.echo("\n" + click.style(f"Error during deletion: {str(e)}", fg='red'), err=True)
        raise
    finally:
        session.close()

@library.command()
@click.option('--calibre-path', type=click.Path(exists=True), default=DEFAULT_CALIBRE_PATH, help="Path to Calibre metadata.db (optional)")
@click.option('--dry-run', is_flag=True, help="Print data without making changes")
def sync_reading(calibre_path: str, dry_run: bool):
    """Sync reading progress from Calibre database

    Example:
        cli library sync-reading  # Sync with default Calibre path
        cli library sync-reading --calibre-path "path/to/metadata.db"  # Use custom path
        cli library sync-reading --dry-run  # Preview changes without applying them
    """
    data = get_reading_progress(calibre_path)
    print_reading_data(data)
    
    if dry_run:
        print("\nDry run - no changes made")
        return
        
    db = Database()
    session: Session = db.get_session()
    user_repo = UserRepository(session)
    
    try:
        warren = user_repo.get_or_create_user("Warren")
        ruth = user_repo.get_or_create_user("Ruth")
        
        print(f"\nUsers:")
        print(f"Warren (ID: {warren.id})")
        print(f"Ruth (ID: {ruth.id})")
        
        total_processed = 0
        warren_updates = 0
        ruth_updates = 0
        
        for entry in data:
            print(f"\nProcessing book: {entry['title']}")
            
            if entry['warren_read_percent'] > 0:
                status = determine_status(entry['warren_read_percent'])
                print(f"Warren's status: {status} ({entry['warren_read_percent']}%)")
                result = user_repo.update_book_status(
                    user_id=warren.id,
                    goodreads_id=entry['goodreads_id'],
                    status=status,
                    source="calibre",
                    started_at=None,
                    finished_at=entry['warren_last_read'] if status == "completed" else None
                )
                if result:
                    warren_updates += 1
                    print("Warren's status updated")
                else:
                    print("Failed to update Warren's status")
            
            if entry['ruth_read_percent'] > 0:
                status = determine_status(entry['ruth_read_percent'])
                print(f"Ruth's status: {status} ({entry['ruth_read_percent']}%)")
                result = user_repo.update_book_status(
                    user_id=ruth.id,
                    goodreads_id=entry['goodreads_id'],
                    status=status,
                    source="calibre",
                    started_at=None,
                    finished_at=entry['ruth_last_read'] if status == "completed" else None
                )
                if result:
                    ruth_updates += 1
                    print("Ruth's status updated")
                else:
                    print("Failed to update Ruth's status")
                    
            total_processed += 1
        
        print(f"\nSync Results:")
        print(f"Total books processed: {total_processed}")
        print(f"Warren's updates: {warren_updates}")
        print(f"Ruth's updates: {ruth_updates}")
        
    finally:
        session.close()

@library.command()
@click.argument('table', type=click.Choice(['book', 'author', 'series', 'library', 'book-similar']))
@click.option('--force/--no-force', default=False, help='Skip confirmation prompt')
@click.option('--verbose/--no-verbose', default=False, help='Show detailed progress')
def reset_sync(table: str, force: bool, verbose: bool):
    """Reset the sync date for all records in a table

    This will set last_synced_at (or similar_synced_at for book-similar) to NULL for all records,
    causing them to be picked up by the next sync operation.

    Valid tables are:
    - book: Reset last_synced_at for all books
    - book-similar: Reset similar_synced_at for all books
    - author: Reset sync dates for all authors
    - series: Reset sync dates for all series
    - library: Reset sync dates for all library entries

    Example:
        cli library reset-sync series  # Reset series sync dates
        cli library reset-sync book --force  # Reset book sync dates without confirmation
        cli library reset-sync book-similar  # Reset similar book sync dates
    """
    db = Database()
    session = Session(db.engine)
    
    try:
        if table == 'book-similar':
            count = session.query(Book).filter(
                (Book.similar_synced_at.isnot(None)) | 
                (Book.similar_synced_at == '')
            ).count()
            
            if count == 0:
                click.echo(click.style("\nNo books found with similar sync dates to reset", fg='yellow'))
                return
                
            click.echo("\n" + click.style(f"This will reset the similar sync date for {count} books", fg='yellow'))
            
            if not force:
                click.confirm("\nAre you sure you want to reset these similar sync dates?", abort=True)
            
            session.query(Book).filter(
                (Book.similar_synced_at.isnot(None)) | 
                (Book.similar_synced_at == '')
            ).update({Book.similar_synced_at: None}, synchronize_session=False)
            session.commit()
            
            click.echo("\n" + click.style("Results:", fg='blue'))
            click.echo(click.style("Reset: ", fg='blue') + 
                       click.style(str(count), fg='green') + 
                       click.style(" book similar sync dates", fg='blue'))
            return
            
        table_map = {
            'book': Book,
            'author': Author,
            'series': Series,
            'library': Library
        }
        
        model = table_map[table]
        count = session.query(model).filter(
            (model.last_synced_at.isnot(None)) | 
            (model.last_synced_at == '')
        ).count()
        
        if count == 0:
            click.echo(click.style(f"\nNo {table} records found with sync dates to reset", fg='yellow'))
            return
            
        click.echo("\n" + click.style(f"This will reset the sync date for {count} {table} records", fg='yellow'))
        
        if not force:
            click.confirm("\nAre you sure you want to reset these sync dates?", abort=True)
        
        session.query(model).filter(
            (model.last_synced_at.isnot(None)) | 
            (model.last_synced_at == '')
        ).update({model.last_synced_at: None}, synchronize_session=False)
        session.commit()
        
        click.echo("\n" + click.style("Results:", fg='blue'))
        click.echo(click.style("Reset: ", fg='blue') + 
                   click.style(str(count), fg='green') + 
                   click.style(f" {table} records", fg='blue'))
                      
    except Exception as e:
        session.rollback()
        click.echo("\n" + click.style(f"Error during reset: {str(e)}", fg='red'), err=True)
        raise
    finally:
        session.close()