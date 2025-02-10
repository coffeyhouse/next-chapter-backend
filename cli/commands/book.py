import click
from sqlalchemy.orm import Session
from core.sa.database import Database
from core.resolvers.book_creator import BookCreator

@click.group()
def book():
    """Book related commands"""
    pass

@book.command()
@click.argument('goodreads_id')
@click.option('--scrape/--no-scrape', default=False, help='Whether to scrape live or use cached data')
def create(goodreads_id: str, scrape: bool):
    """Create a book from Goodreads ID
    
    Example:
        cli book create 54493401  # Create Project Hail Mary
        cli book create 7235533 --scrape  # Create The Way of Kings with fresh data
    """
    # Initialize database and session
    db = Database()
    session = Session(db.engine)
    
    try:
        # Create book creator
        creator = BookCreator(session, scrape=scrape)
        
        # Create the book
        book = creator.create_book_from_goodreads(goodreads_id)
        
        if book is None:
            click.echo(f"Book with Goodreads ID {goodreads_id} already exists or could not be created")
            return
        
        # Print success message with book details
        click.echo(f"Successfully created book:")
        click.echo(f"  Title: {book.title}")
        click.echo(f"  Author(s): {', '.join(author.name for author in book.authors)}")
        click.echo(f"  Genre(s): {', '.join(genre.name for genre in book.genres)}")
        if book.series:
            click.echo(f"  Series: {', '.join(series.title for series in book.series)}")
        
    except Exception as e:
        click.echo(f"Error creating book: {str(e)}", err=True)
        raise
    finally:
        session.close()
