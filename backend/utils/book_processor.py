from typing import Dict, List, Any, Tuple, Optional
import click
import sqlite3
from datetime import datetime
from backend.utils.data_transformer import transform_book_data
from backend.scrapers.book import scrape_book
from backend.scrapers.editions import scrape_editions
from backend.db.db_operations import DatabaseOperations
from backend.utils.rate_limiter import RateLimiter

class BookProcessor:
    def __init__(self, db_path: str, scrape: bool = False):
        self.db = DatabaseOperations(db_path)
        self.scrape = scrape
        self.rate_limiter = RateLimiter()
        
    def exists_by_goodreads_id(self, book_id: str) -> Tuple[bool, bool]:
        """
        Check if a book exists by its Goodreads ID and if it has metadata.
        
        Args:
            book_id: Goodreads book ID
            
        Returns:
            Tuple[bool, bool]: (exists, has_metadata)
        """
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT goodreads_id, last_synced_at 
                    FROM books 
                    WHERE goodreads_id = ?
                    """,
                    (book_id,)
                )
                result = cursor.fetchone()
                if result:
                    has_metadata = result[1] is not None
                    return True, has_metadata
                return False, False
        except Exception as e:
            click.echo(f"Error checking book by Goodreads ID: {str(e)}")
            return False, False

    def check_book_exists(self, book_id: str, book_info: Dict[str, Any]) -> Tuple[bool, bool]:
        """Check if book exists using multiple methods."""
        click.echo(f"DEBUG: Checking existence for book_id: {book_id}")
        
        # First try Goodreads ID
        exists, has_metadata = self.exists_by_goodreads_id(book_id)
        if exists:
            click.echo(f"Book already exists with metadata, skipping...")
            return exists, has_metadata

        # Then try metadata
        similar_books_match = self.exists_by_metadata(book_info)
        if similar_books_match:
            click.echo(f"Book exists by metadata match, skipping...")
            return True, False  # Found by metadata but no details
        
        # If we got here, no match found
        return False, False

    def exists_by_metadata(self, book_info: Dict[str, Any]) -> bool:
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                # Check similar_books_id from various possible locations
                work_id = None
                
                # Debug logging for inspection
                click.echo(f"DEBUG: Raw book info for metadata check: {book_info}")
                
                if isinstance(book_info, dict):
                    work_id = book_info.get('similar_books_id')
                    if work_id:
                        cursor = conn.execute(
                            "SELECT goodreads_id FROM books WHERE similar_books_id = ?",
                            (work_id,)
                        )
                        result = cursor.fetchone()
                        exists = result is not None
                        if exists:
                            click.echo(f"DEBUG: Found existing book with similar_books_id {work_id}: {result[0]}")
                            return True
                        click.echo(f"DEBUG: No existing book found with similar_books_id {work_id}")
                        
                click.echo(f"DEBUG: No similar_books_id found in book data to check")
                return False
                    
        except Exception as e:
            click.echo(f"Error checking book by metadata: {str(e)}")
            return False
    
    def process_book_list(
        self, 
        books: List[Dict[str, Any]], 
        source: str,
        description: str = "books"
    ) -> Tuple[int, int, int]:
        """
        Process a list of books, scraping and inserting each one.
        
        Returns:
            Tuple[int, int, int]: (total, successful, skipped)
        """
        total_books = len(books)
        successful_books = 0
        skipped_books = 0
        
        click.echo(f"\nProcessing {total_books} {description}")
        
        for i, book in enumerate(books, 1):
            book_id = book['id']
            click.echo(f"\nProcessing book {i}/{total_books}: {book['title']} ({book_id})")
            
            # First check if book exists and has metadata
            exists, has_metadata = self.exists_by_goodreads_id(book_id)
            if exists and has_metadata:
                click.echo(f"Book already exists with metadata, skipping...")
                skipped_books += 1
                continue

            # If it doesn't exist or doesn't have metadata, process it
            success, was_skipped = self.process_single_book_id(book_id, source)
            if success:
                if was_skipped:
                    skipped_books += 1
                else:
                    successful_books += 1
                
        return total_books, successful_books, skipped_books
    
    def is_english_book(self, book_info: Dict[str, Any]) -> bool:
        """Check if a book is in English."""
        language = book_info.get('details', {}).get('language')
        if language and language.lower() == 'english':
            return True
        click.echo(f"Book is not in English (language: {language})")
        return False
    
    def find_valid_edition(self, book_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Try to find an edition that is in English and has a valid format."""
        try:
            work_id = book_info.get('similar_books_id')
            if not work_id:
                click.echo("No work ID available to check editions")
                return None

            click.echo(f"Searching for valid edition using work ID: {work_id}")
            
            if self.scrape:
                self.rate_limiter.delay()

            editions_result = scrape_editions(work_id, scrape=self.scrape)
            if not editions_result:
                click.echo("Failed to retrieve editions")
                return None
            
            if isinstance(editions_result, tuple) and len(editions_result) == 2:
                first_edition, english_edition = editions_result
                if isinstance(english_edition, dict):
                    if self._get_valid_format(english_edition):
                        click.echo(f"Found valid English edition: {english_edition.get('title', {}).get('title', 'Unknown')}")
                        return english_edition
                    else:
                        click.echo(f"English edition found but format invalid: {english_edition.get('details', {}).get('format', 'Unknown')}")
                else:
                    click.echo(f"Unexpected english_edition format: {type(english_edition)}")
            else:
                click.echo(f"Unexpected editions_result format: {type(editions_result)}")
            
            click.echo("No valid English edition found")
            return None

        except Exception as e:
            click.echo(f"Error finding valid edition: {str(e)}")
            click.echo(f"Exception details: {type(e).__name__}")
            import traceback
            click.echo(traceback.format_exc())
            return None
    
    def _get_valid_format(self, book_info: Dict[str, Any]) -> bool:
        """
        Check if book has a valid format and page count.
        Returns True if valid format is found, False otherwise.
        """
        # Preferred format order
        preferred_formats = [
            'Kindle Edition',
            'Paperback',
            'Hardcover', 
            'Mass Market Paperback',
            'ebook'
        ]
        
        # Get format and pages from book details
        book_format = book_info.get('details', {}).get('format')
        pages = book_info.get('details', {}).get('pages')
        
        # Debug logging
        click.echo(f"Book format: {book_format}")
        click.echo(f"Page count: {pages}")
        
        # Check if format is in preferred list and has page count
        if book_format in preferred_formats and pages:
            return True
        
        return False
    
    def _process_single_book(self, book_id: str, source: str, exists: bool = False, has_metadata: bool = False, calibre_id: int = None) -> bool:
        """Process a single book by ID."""
        try:
            if self.scrape:
                self.rate_limiter.delay()
            
            book_info = scrape_book(book_id, scrape=self.scrape)
            if not book_info:
                click.echo(f"Failed to scrape book ID: {book_id}")
                return False
            
            # Check format and language, try to find valid edition if needed
            if not self._get_valid_format(book_info) or not self.is_english_book(book_info):
                valid_edition = self.find_valid_edition(book_info)
                if not valid_edition:
                    click.echo("No suitable edition found (needs to be English with valid format)")
                    return False
                
                edition_id = valid_edition.get('id') or valid_edition.get('goodreads_id')
                if not edition_id:
                    click.echo("Valid edition lacks an ID")
                    return False
                    
                edition_exists, edition_has_metadata = self.check_book_exists(edition_id, valid_edition)
                if edition_exists and edition_has_metadata:
                    click.echo(f"Valid edition already exists with metadata")
                    return True
                
                book_info = valid_edition
                book_id = edition_id
                exists = edition_exists
                has_metadata = edition_has_metadata

            book_info['source'] = source
            if calibre_id:
                book_info['calibre_id'] = calibre_id
            book_tables = transform_book_data(book_info)

            # Get existing timestamps if book exists
            existing_timestamps = {}
            if exists:
                with sqlite3.connect(self.db.db_path) as conn:
                    cursor = conn.execute(
                        "SELECT created_at FROM books WHERE goodreads_id = ?",
                        (book_id,)
                    )
                    result = cursor.fetchone()
                    if result:
                        existing_timestamps["created_at"] = result[0]

            # Update timestamps
            now = datetime.now().isoformat()
            for book in book_tables.get('book', []):
                if book['goodreads_id'] == book_id:
                    if exists:
                        if not has_metadata:
                            book['updated_at'] = now
                            book['last_synced_at'] = now
                        book['created_at'] = existing_timestamps.get(
                            "created_at", 
                            book.get('created_at', now)
                        )
                    else:
                        book.setdefault('created_at', now)
                        book['updated_at'] = now
                        book['last_synced_at'] = now

            if self.db.insert_transformed_data(book_tables):
                action = "updated" if exists else "inserted"
                click.echo(f"Successfully {action} book: {book_info.get('title', {}).get('title', 'Unknown')}")
                return True
            
            click.echo(f"Failed to {'update' if exists else 'insert'} book")
            return False

        except Exception as e:
            click.echo(f"Error processing book {book_id}: {str(e)}")
            return False
            
    def process_single_book_id(self, book_id: str, source: str, calibre_id: int = None) -> Tuple[bool, bool]:
        """Process a single book by its Goodreads ID."""
        click.echo(f"\nProcessing book: {book_id}")
        
        if self.scrape:
            self.rate_limiter.delay()
            
        book_info = scrape_book(book_id, scrape=self.scrape)
        if not book_info:
            return False, False  # Failed, not skipped
            
        exists, has_metadata = self.check_book_exists(book_id, book_info)
        if exists:
            click.echo(f"Book already exists{' with metadata' if has_metadata else ''}")
            return True, True  # Success and skipped
        
        success = self._process_single_book(book_id, source, exists, has_metadata, calibre_id)
        return success, False  # If we process it, it's not skipped

    def print_stats(self, total: int, successful: int, skipped: int) -> None:
        """Print processing and database statistics"""
        click.echo(f"\nTotal books processed: {total}")
        click.echo(f"Successfully processed: {successful}")
        click.echo(f"Skipped books: {skipped}")