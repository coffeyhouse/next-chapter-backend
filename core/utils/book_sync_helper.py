# core/utils/book_sync_helper.py
from typing import List
from sqlalchemy.orm import Session
from core.sa.repositories.book import BookRepository
from core.sa.models import BookScraped
from core.resolvers.book_creator import BookCreator

def process_book_ids(session: Session, goodreads_ids: List[str], source: str, scrape: bool = False, force_update: bool = False):
    """
    Processes a list of Goodreads IDs:
      - If a book exists in the Book table (by goodreads_id) and force_update is False, it is skipped.
      - If force_update is True, existing books will be updated with fresh data.
      - If a scrape record exists in BookScraped with a work_id that maps to a book in Book, it is skipped.
      - Otherwise, scrape the book data and create a new Book record.
    
    Args:
        session: SQLAlchemy session
        goodreads_ids: List of Goodreads IDs to process
        source: Source of the books
        scrape: Whether to scrape live or use cached data
        force_update: Whether to update existing books
    
    Returns:
        List of newly created or updated Book objects.
    """
    created_books = []
    book_repo = BookRepository(session)
    creator = BookCreator(session, scrape=scrape)
    
    for gr_id in goodreads_ids:
        # Check if the book already exists by goodreads_id.
        existing_book = book_repo.get_by_goodreads_id(gr_id)
        if existing_book:
            if force_update:
                # Update the existing book with fresh data
                updated_book = creator.update_book_from_goodreads(gr_id, source=source)
                if updated_book:
                    created_books.append(updated_book)
            continue
        
        # Check the BookScraped table for an existing scrape record.
        scraped = session.query(BookScraped).filter_by(goodreads_id=gr_id).first()
        if scraped and scraped.work_id:
            if book_repo.get_by_work_id(scraped.work_id):
                continue
        
        # Otherwise, scrape and create the book.
        book = creator.create_book_from_goodreads(gr_id, source=source)
        if book:
            created_books.append(book)
    
    return created_books
