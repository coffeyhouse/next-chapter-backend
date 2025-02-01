# backend/cli/commands/book.py
from typing import Optional, List, Dict, Any
import click
from datetime import datetime
from ..base import BaseCommand
from backend.scrapers.book import scrape_book
from backend.scrapers.editions import scrape_editions

class BookCommand(BaseCommand):
    """Book-related commands"""
    
    def update_book(self, book_id: str) -> bool:
        """Update a single book"""
        now = datetime.now().isoformat()
        
        click.echo("\nStarting book update process...")
        
        # Get initial book details
        book_info = scrape_book(book_id, scrape=self.scrape)
        if not book_info:
            click.echo(f"Failed to get details for book ID: {book_id}")
            return False

        click.echo("\nInitial book info:")
        click.echo(f"Title: {book_info.get('title', 'No title')}")
        click.echo(f"Language: {book_info.get('details', {}).get('language', 'No language')}")
        click.echo(f"Created at: {book_info.get('created_at', 'No created_at')}")
        
        # Check language and try to find English edition if needed
        if (not book_info.get('details', {}).get('language') or 
            book_info['details']['language'].lower() != 'english'):
            
            click.echo("\nNon-English book detected, looking for English edition...")
            work_id = book_info.get('similar_books_id')
            if work_id:
                first_edition, english_edition = scrape_editions(
                    work_id,
                    scrape=self.scrape
                )
                if english_edition:
                    click.echo("\nBefore switching to English edition:")
                    click.echo(f"Original timestamps: created={book_info.get('created_at')}, updated={book_info.get('updated_at')}")
                    
                    # Create new dict with essential metadata
                    updated_info = {
                        'created_at': now,
                        'updated_at': now,
                        'goodreads_id': english_edition.get('goodreads_id', book_id)
                    }
                    updated_info.update(english_edition)
                    
                    click.echo("\nAfter preparing English edition data:")
                    click.echo(f"New timestamps: created={updated_info.get('created_at')}, updated={updated_info.get('updated_at')}")
                    click.echo(f"Book ID: {updated_info.get('goodreads_id')}")
                    click.echo(f"Title: {updated_info.get('title', 'No title')}")
                    
                    book_info = updated_info
                    click.echo("Switched to English edition")
                else:
                    click.echo("No English edition found")
        
        click.echo("\nFinal data before database update:")
        click.echo(f"Goodreads ID: {book_info.get('goodreads_id')}")
        click.echo(f"Title: {book_info.get('title', 'No title')}")
        click.echo(f"Language: {book_info.get('details', {}).get('language', 'No language')}")
        click.echo(f"Created at: {book_info.get('created_at', 'No created_at')}")
        click.echo(f"Updated at: {book_info.get('updated_at', 'No updated_at')}")
        
        # Let the database layer handle the update
        success = self.db.update_book(book_info)
        click.echo(f"\nDatabase update {'succeeded' if success else 'failed'}")
        return success

    def update_books(
        self,
        book_ids: Optional[List[str]] = None,
        unsynced_only: bool = False,
        limit: Optional[int] = None
    ) -> int:
        """Update multiple books
        
        Args:
            book_ids: Optional list of specific book IDs to update
            unsynced_only: If True and no book_ids provided, only update unsynced books
            limit: Optional limit on number of books to process
            
        Returns:
            Number of successfully processed books
        """
        if book_ids:
            books = [{'goodreads_id': id} for id in book_ids]
        elif unsynced_only:
            books = self.db.get_unsynced_books(limit)
            if not books:
                click.echo("No unsynced books found")
                return 0
        else:
            books = self.db.get_all('books', limit=limit)
            if not books:
                click.echo("No books found")
                return 0
        
        def process_book(book: dict) -> bool:
            return self.update_book(book['goodreads_id'])
            
        return self.process_items(books, process_book, "books")