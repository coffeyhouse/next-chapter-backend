# core/cli/commands/library.py
import click
from core.database import GoodreadsDB
from sqlalchemy.orm import Session
from core.sa.database import Database
from core.resolvers.book_creator import BookCreator
from core.resolvers.book_resolver import BookResolver
from core.sa.models import Book, Author, Genre, Series, BookAuthor, BookGenre, BookSeries, Library
import sqlite3

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
    
    This command uses the new SQLAlchemy-based BookCreator to import books from Calibre.
    It will create book records with proper relationships for authors, genres, and series.
    
    Example:
        cli library import-calibre-sa --calibre-path "path/to/metadata.db"
        cli library import-calibre-sa --limit 10 --scrape  # Import 10 books with fresh data
    """
    if verbose:
        click.echo(click.style("\nImporting from Calibre: ", fg='blue') + 
                  click.style(calibre_path, fg='cyan'))
    
    # Initialize database and session
    db = Database()
    session = Session(db.engine)
    
    try:
        # Create book creator and resolver
        creator = BookCreator(session, scrape=scrape)
        resolver = BookResolver(scrape=scrape)
        
        # Get existing IDs from Library table
        existing_library_ids = set(
            id_tuple[0] for id_tuple in 
            session.query(Library.goodreads_id)
            .filter(Library.goodreads_id.isnot(None))
            .all()
        )
        
        # Get existing work IDs from Library table
        existing_work_ids = set(
            id_tuple[0] for id_tuple in 
            session.query(Library.work_id)
            .all()
        )
        
        if verbose:
            click.echo(click.style("\nFound existing library books:", fg='blue'))
            click.echo(click.style(f"  - {len(existing_library_ids)} by Goodreads ID", fg='cyan'))
            click.echo(click.style(f"  - {len(existing_work_ids)} by Work ID", fg='cyan'))
        
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
            
            # Filter out books that already exist by Goodreads ID
            new_books = [
                book for book in calibre_books 
                if book[2] not in existing_library_ids
            ]
            
            if limit:
                new_books = new_books[:limit]
            
            if verbose:
                click.echo(click.style(f"\nFound ", fg='blue') + 
                          click.style(f"{len(new_books)}", fg='cyan') + 
                          click.style(" new books to process", fg='blue'))
                if len(new_books) > 0:
                    click.echo(click.style("First new book:", fg='blue'))
                    click.echo(click.style(f"  - Title: {new_books[0][1]}", fg='cyan'))
                    click.echo(click.style(f"  - Goodreads ID: {new_books[0][2]}", fg='cyan'))
                    click.echo(click.style(f"  - ISBN: {new_books[0][3]}", fg='cyan'))
                click.echo(click.style("\nExisting IDs:", fg='blue'))
                click.echo(click.style(f"  - Library IDs: {existing_library_ids}", fg='cyan'))
                click.echo(click.style(f"  - Work IDs: {existing_work_ids}", fg='cyan'))
            
            processed = 0
            imported = 0
            skipped = []
            
            # Disable other output during progress bar unless verbose
            with click.progressbar(
                new_books,
                label=click.style('Processing books', fg='blue'),
                item_show_func=lambda b: click.style(b[1], fg='cyan') if b and verbose else None,
                show_eta=True,
                show_percent=True,
                width=50
            ) as books_iter:
                for book in books_iter:
                    calibre_data = {
                        'calibre_id': book[0],
                        'title': book[1],
                        'goodreads_id': book[2],
                        'isbn': book[3],
                        'source': 'library'
                    }
                    
                    try:
                        # Try to resolve the book data first to get work_id
                        book_data = resolver.resolve_book(calibre_data['goodreads_id'])
                        if not book_data:
                            skipped.append({
                                'title': calibre_data['title'],
                                'goodreads_id': calibre_data['goodreads_id'],
                                'reason': "Failed to resolve book data from Goodreads",
                                'color': 'red'
                            })
                            processed += 1
                            continue
                            
                        # Check if book exists by work_id
                        if book_data.get('work_id') in existing_work_ids:
                            existing_book = session.query(Book).filter_by(
                                work_id=book_data['work_id']
                            ).first()
                            skipped.append({
                                'title': calibre_data['title'],
                                'goodreads_id': calibre_data['goodreads_id'],
                                'reason': f"Book already exists with work_id {book_data['work_id']} (title: {existing_book.title})",
                                'color': 'yellow'
                            })
                            processed += 1
                            continue
                        
                        # Create the book using the resolved data
                        book_obj = creator.create_book(book_data)
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
                            imported += 1
                        else:
                            skipped.append({
                                'title': calibre_data['title'],
                                'goodreads_id': calibre_data['goodreads_id'],
                                'reason': "Failed to create book for unknown reason",
                                'color': 'red'
                            })
                    except Exception as e:
                        skipped.append({
                            'title': calibre_data['title'],
                            'goodreads_id': calibre_data['goodreads_id'],
                            'reason': f"Error: {str(e)}",
                            'color': 'red'
                        })
                    
                    processed += 1
            
            # Print results
            click.echo("\n" + click.style("Results:", fg='blue'))
            click.echo(click.style("Processed: ", fg='blue') + 
                      click.style(str(processed), fg='cyan') + 
                      click.style(" books", fg='blue'))
            click.echo(click.style("Imported: ", fg='blue') + 
                      click.style(str(imported), fg='green') + 
                      click.style(" books", fg='blue'))
            
            if skipped and verbose:
                click.echo("\n" + click.style("Skipped books:", fg='yellow'))
                for skip_info in skipped:
                    click.echo("\n" + click.style(f"Title: {skip_info['title']}", fg=skip_info['color']))
                    click.echo(click.style(f"Goodreads ID: {skip_info['goodreads_id']}", fg=skip_info['color']))
                    click.echo(click.style(f"Reason: {skip_info['reason']}", fg=skip_info['color']))
            elif skipped:
                click.echo(click.style(f"\nSkipped {len(skipped)} books. ", fg='yellow') + 
                          click.style("Use --verbose to see details.", fg='blue'))
            
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
            'book_series': session.query(BookSeries).count()
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
        
        with click.progressbar(length=8, label='Emptying database') as bar:
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
        
        session.commit()
        click.echo(click.style("\nSuccessfully emptied database", fg='green'))
        
    except Exception as e:
        session.rollback()
        click.echo(click.style(f"\nError emptying database: {str(e)}", fg='red'))
        raise
    finally:
        session.close()