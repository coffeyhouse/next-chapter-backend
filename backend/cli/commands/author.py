# backend/cli/commands/author.py
from typing import Optional
import click
from ..base import BaseCommand
from backend.scrapers.author import scrape_author
from backend.scrapers.author_books import scrape_author_books

class AuthorCommand(BaseCommand):
    """Author-related commands"""
    
    def update_authors(self, limit: Optional[int] = None) -> int:
        """Update author information from Goodreads
        
        Args:
            limit: Optional limit on number of authors to process
            
        Returns:
            Number of successfully processed authors
        """
        # Get unsynced authors
        authors = self.db.get_unsynced_authors(limit)
        if not authors:
            click.echo("No unsynced authors found")
            return 0
            
        def process_author(author: dict) -> bool:
            # Get author details
            author_info = scrape_author(
                author['goodreads_id'], 
                scrape=self.scrape
            )
            if not author_info:
                click.echo(f"Failed to get details for: {author['name']}")
                return False
                
            # Update author record
            if not self.db.update_author(author_info):
                return False
                
            # Get and process author's books
            return self.process_author_books(author['goodreads_id'])
            
        return self.process_items(authors, process_author, "authors")
        
    def process_author_books(self, author_id: str) -> bool:
        """Process all books by an author"""
        # Get author's books
        result = scrape_author_books(author_id, scrape=self.scrape)
        if not result:
            click.echo(f"Failed to get books for author ID: {author_id}")
            return False
            
        books = result.get('books', [])
        if not books:
            click.echo("No books found")
            return True
            
        def process_book(book: dict) -> bool:
            return self.db.update_book(book)
            
        success_count = self.process_items(books, process_book, "books")
        return success_count > 0