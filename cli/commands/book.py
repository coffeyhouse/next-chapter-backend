import click
from sqlalchemy.orm import Session
from core.sa.database import Database
from core.utils.book_sync_helper import process_book_ids
from typing import Optional
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
from core.exclusions import get_exclusion_reason
from core.sa.models import Book, BookAuthor, BookGenre
from core.sa.models.book import HiddenReason

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
        # Use process_book_ids to standardize the existence/scrape logic
        books = process_book_ids(session, [goodreads_id], source='book', scrape=scrape)
        book_obj = books[0] if books else None
        
        if book_obj is None:
            click.echo(f"Book with Goodreads ID {goodreads_id} already exists or could not be created")
            return
        
        # Print success message with book details
        click.echo("Successfully created book:")
        click.echo(f"  Title: {book_obj.title}")
        click.echo(f"  Author(s): {', '.join(author.name for author in book_obj.authors)}")
        click.echo(f"  Genre(s): {', '.join(genre.name for genre in book_obj.genres)}")
        if book_obj.series:
            click.echo(f"  Series: {', '.join(series.title for series in book_obj.series)}")
        
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

def _check_combined_titles(session: Session, book: Book) -> tuple[bool, list[tuple[str, str]]]:
    """Check if a book title appears to contain multiple books by comparing with other titles from the same author(s)
    
    Returns:
        Tuple of (is_combined, list of matched parts with their work_ids)
    """
    # Common separators that might indicate multiple books
    separators = [
        '/',           # "Book1/Book2"
        ' & ',         # "Book1 & Book2"
        ' and ',       # "Book1 and Book2"
        ', ',          # "Book1, Book2"
        ': ',          # "Collection: Book1, Book2"
    ]
    
    # Get all authors for this book
    author_ids = [ba.author_id for ba in book.book_authors]
    if not author_ids:
        return False, []
        
    # Get all books by these authors
    other_books = (
        session.query(Book)
        .join(BookAuthor)
        .filter(BookAuthor.author_id.in_(author_ids))
        .filter(Book.work_id != book.work_id)  # Exclude current book
        .all()
    )
    
    # Get all titles by these authors (excluding current book)
    author_titles = {b.title.lower().strip(): b for b in other_books}
    
    # Check the current book title against common patterns
    title = book.title
    
    # First check if the title contains any separators
    if not any(sep in title for sep in separators):
        return False, []
        
    # Split the title by various separators and clean up the parts
    parts = []
    working_title = title
    
    # Handle "Collection:" or similar prefixes
    if ': ' in working_title:
        _, working_title = working_title.split(': ', 1)
    
    # Split by various separators
    for sep in separators:
        if sep in working_title:
            # Split and clean up parts
            split_parts = [p.strip() for p in working_title.split(sep)]
            # Only add non-empty parts that don't contain other separators
            for part in split_parts:
                if part and not any(s in part for s in separators):
                    parts.append(part)
            
    # Remove duplicates and empty strings
    parts = [p for p in set(parts) if p]
    
    # Only consider it a match if:
    # 1. We have at least 2 parts
    # 2. ALL parts match other book titles exactly
    # 3. The matches are different books (different work IDs)
    # 4. The title contains one of our explicit separators
    if len(parts) >= 2:
        matches = []
        for part in parts:
            part_lower = part.lower()
            if part_lower in author_titles:
                matched_book = author_titles[part_lower]
                matches.append((matched_book.title, matched_book.work_id))
        
        # All parts must match exactly and be different books
        if len(matches) == len(parts) and len(set(m[1] for m in matches)) == len(matches):
            return True, matches
        
    return False, []

@book.command()
@click.option('--limit', default=None, type=int, help='Limit number of books to check')
@click.option('--verbose/--no-verbose', default=False, help='Show detailed progress')
@click.option('--work-id', default=None, help='Check a specific book by work ID')
def check_exclusions(limit: Optional[int], verbose: bool, work_id: Optional[str]):
    """Check existing books against exclusion rules and update their hidden status.
    
    Example:
        cli book check-exclusions  # Check all books
        cli book check-exclusions --limit 100  # Check first 100 books
        cli book check-exclusions --verbose  # Show detailed progress of changes
        cli book check-exclusions --work-id 207476286  # Check specific book
    """
    # Initialize database and session
    db = Database()
    session = Session(db.engine)
    
    try:
        # Get books to check
        if work_id:
            books = [session.query(Book).filter(Book.work_id == work_id).first()]
            if not books[0]:
                click.echo(f"\nNo book found with work ID: {work_id}")
                return
            total_books = 1
        else:
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
        combined_titles = []
        
        click.echo(f"\nChecking {total_books} books against exclusion rules...")
        
        for i, book in enumerate(books, 1):
            # Check for combined titles
            is_combined, matches = _check_combined_titles(session, book)
            if is_combined:
                combined_titles.append((book, matches))
                # Mark as hidden with combined edition reason
                if not book.hidden or book.hidden_reason != HiddenReason.COMBINED_EDITION:
                    book.hidden = True
                    book.hidden_reason = HiddenReason.COMBINED_EDITION
                    updated_books.append((book, f"Hidden: Combined edition containing {', '.join(m[0] for m in matches)}"))
                if verbose:
                    click.echo(f"\nCombined title found: {book.title}")
                    click.echo("Contains:")
                    for title, work_id in matches:
                        click.echo(f"  - {title} (work_id: {work_id})")
                    click.echo("Authors:")
                    for ba in book.book_authors:
                        click.echo(f"  - {ba.author.name}")
                continue
                
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
        
        # Print combined titles results
        if combined_titles:
            click.echo("\nFound combined titles:")
            for book, matches in combined_titles:
                click.echo(f"\n{book.title} (work_id: {book.work_id})")
                click.echo("Contains:")
                for title, work_id in matches:
                    click.echo(f"  - {title} (work_id: {work_id})")
                click.echo("Authors:")
                for ba in book.book_authors:
                    click.echo(f"  - {ba.author.name}")
        
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
