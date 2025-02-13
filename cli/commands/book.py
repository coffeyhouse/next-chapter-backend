import click
from sqlalchemy.orm import Session
from core.sa.database import Database
from core.resolvers.book_creator import BookCreator
from typing import Optional
from bs4 import BeautifulSoup

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

@book.command()
@click.option('--force/--no-force', default=False, help='Force redownload of all images')
@click.option('--scrape/--no-scrape', default=True, help='Whether to scrape live or use cached data')
@click.option('--limit', default=None, type=int, help='Limit number of books to process')
def fix_covers(force: bool, scrape: bool, limit: Optional[int]):
    """Fix book cover paths to use frontend public directory"""
    from sqlalchemy.orm import Session
    from core.sa.database import Database
    from core.sa.repositories.book import BookRepository
    from core.utils.image import download_book_cover
    from core.scrapers.book_scraper import BookScraper
    import shutil
    from pathlib import Path
    import requests
    from typing import Optional
    
    # Initialize database and scrapers
    db = Database()
    session = Session(db.engine)
    repo = BookRepository(session)
    scraper = BookScraper(scrape=scrape)
    
    try:
        # Get all books with image URLs
        books = repo.get_all_books_with_images()
        
        # Apply limit if specified
        if limit:
            books = books[:limit]
            click.echo(f"\nLimiting to {limit} books")
        
        # Create frontend covers directory if it doesn't exist
        covers_dir = Path("C:/Code/calibre_companion/frontend/public/covers")
        covers_dir.mkdir(parents=True, exist_ok=True)
        
        click.echo(f"\nProcessing {len(books)} books with covers...")
        
        for i, book in enumerate(books, 1):
            try:
                click.echo(f"[{i}/{len(books)}] Processing: {book.title}")
                
                # Get fresh book data to ensure we have the latest cover URL
                book_data = scraper.scrape_book(book.goodreads_id)
                if not book_data:
                    continue
                
                # Get cover URL from scraped data
                cover_url = scraper._extract_cover_url(BeautifulSoup(scraper._read_html(book.goodreads_id), 'html.parser'))
                if not cover_url:
                    continue
                
                try:
                    # Download image
                    response = requests.get(cover_url)
                    if not response.ok:
                        continue
                        
                    # Save image
                    image_path = covers_dir / f"{book.work_id}.jpg"
                    with open(image_path, 'wb') as f:
                        f.write(response.content)
                        
                    if not image_path.exists():
                        continue
                        
                    # Update database
                    new_url = f"/covers/{book.work_id}.jpg"
                    book.image_url = new_url
                    session.add(book)
                    session.commit()
                    
                    click.echo(f"  Updated cover for: {book.title}")
                        
                except (requests.RequestException, IOError, Exception):
                    continue
                
            except Exception as e:
                session.rollback()
                continue
                
    except Exception as e:
        click.echo(f"\nError during cover update: {e}", err=True)
        raise
    finally:
        session.close()
        
    click.echo("\nFinished updating book covers")
