import click
from sqlalchemy.orm import Session
from core.sa.database import Database
from core.resolvers.book_creator import BookCreator
from typing import Optional
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
from core.exclusions import get_exclusion_reason
from core.sa.models import Book, BookAuthor, BookGenre
from core.models.book import HiddenReason

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
        # Get books that need image processing
        books = repo.get_all_books_with_images(force=force)
        
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
                book_data = scraper.scrape(book.goodreads_id)
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
                        
                    # Process image
                    img = Image.open(BytesIO(response.content))
                    
                    # Convert to RGB if necessary
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                    
                    # Resize if height exceeds max_height
                    max_height = 300
                    if img.height > max_height:
                        ratio = max_height / img.height
                        new_width = int(img.width * ratio)
                        img = img.resize((new_width, max_height), Image.Resampling.LANCZOS)
                        
                    # Save as WebP
                    image_path = covers_dir / f"{book.work_id}.webp"
                    img.save(image_path, format='WEBP', quality=85, method=6)
                    
                    # Update database
                    new_url = f"/covers/{book.work_id}.webp"
                    book.image_url = new_url
                    session.add(book)
                    session.commit()
                    
                    click.echo(f"  Updated cover for: {book.title}")
                        
                except (requests.RequestException, IOError, Exception) as e:
                    click.echo(f"  Error processing image: {e}")
                    continue
                
            except Exception as e:
                session.rollback()
                click.echo(f"  Error processing book: {e}")
                continue
                
    except Exception as e:
        click.echo(f"\nError during cover update: {e}", err=True)
        raise
    finally:
        session.close()
        
    click.echo("\nFinished updating book covers")

@book.command()
@click.option('--limit', default=None, type=int, help='Limit number of books to check')
@click.option('--verbose/--no-verbose', default=False, help='Show detailed progress')
def check_exclusions(limit: Optional[int], verbose: bool):
    """Check existing books against exclusion rules and update their hidden status.
    
    Example:
        cli book check-exclusions  # Check all books
        cli book check-exclusions --limit 100  # Check first 100 books
        cli book check-exclusions --verbose  # Show detailed progress of changes
    """
    # Initialize database and session
    db = Database()
    session = Session(db.engine)
    
    try:
        # Get all books with their relationships
        query = (
            session.query(Book)
            .outerjoin(BookAuthor)
            .outerjoin(BookGenre)
        )
        
        if limit:
            query = query.limit(limit)
            
        books = query.all()
        total_books = len(books)
        excluded_books = []
        updated_books = []
        
        click.echo(f"\nChecking {total_books} books against exclusion rules...")
        
        for i, book in enumerate(books, 1):
            # Convert SQLAlchemy model to dict format expected by exclusions
            book_dict = {
                "title": book.title,
                "goodreads_id": book.goodreads_id,
                "work_id": book.work_id,
                "pages": book.pages,
                "goodreads_votes": book.goodreads_votes,
                "description": book.description,
                "published_state": book.published_state,
                "genres": [{"name": genre.name} for genre in book.genres]
            }
            
            # Check against exclusion rules
            exclusion_result = get_exclusion_reason(book_dict)
            if exclusion_result:
                # Update the book if needed
                if not book.hidden or book.hidden_reason != exclusion_result.hidden_reason:
                    book.hidden = True
                    book.hidden_reason = exclusion_result.hidden_reason
                    updated_books.append((book, f"Hidden: {exclusion_result.reason}"))
                    if verbose:
                        click.echo(f"[{i}/{total_books}] {book.title} - Now hidden: {exclusion_result.reason}")
                
                excluded_books.append((book, exclusion_result.reason))
            else:
                # If book was previously hidden due to exclusion rules, unhide it
                if book.hidden and book.hidden_reason in [
                    HiddenReason.LOW_VOTE_COUNT,
                    HiddenReason.NO_DESCRIPTION,
                    HiddenReason.EXCEEDS_PAGE_LENGTH,
                    HiddenReason.EXCLUDED_GENRE,
                    HiddenReason.TITLE_PATTERN_MATCH,
                    HiddenReason.TITLE_NUMBER_PATTERN
                ]:
                    book.hidden = False
                    book.hidden_reason = None
                    updated_books.append((book, "Unhidden: no longer meets exclusion criteria"))
                    if verbose:
                        click.echo(f"[{i}/{total_books}] {book.title} - Now unhidden (no longer meets exclusion criteria)")
        
        # Commit changes
        if updated_books:
            session.commit()
            click.echo(f"\nUpdated {len(updated_books)} books:")
            for book, change in updated_books:
                click.echo(f"- {book.title} ({book.work_id})")
                click.echo(f"  {change}")
        else:
            click.echo("\nNo changes needed - all books are correctly marked")
            
    except Exception as e:
        click.echo(f"\nError checking exclusions: {e}", err=True)
        raise
    finally:
        session.close()
