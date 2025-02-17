# core/utils/book_sync_helper.py
from typing import List
from sqlalchemy.orm import Session
from core.sa.repositories.book import BookRepository
from core.sa.models import BookScraped
from core.resolvers.book_creator import BookCreator

def process_book_ids(session: Session, goodreads_ids: List[str], source: str, scrape: bool = False):
    """
    Processes a list of Goodreads IDs:
      - If a book exists in the Book table (by goodreads_id), it is skipped.
      - If a scrape record exists in BookScraped with a work_id that maps to a book in Book, it is skipped.
      - Otherwise, scrape the book data and create a new Book record.
    
    Returns a list of newly created Book objects.
    """
    created_books = []
    book_repo = BookRepository(session)
    creator = BookCreator(session, scrape=scrape)
    
    for gr_id in goodreads_ids:
        # Check if the book already exists by goodreads_id.
        if book_repo.get_by_goodreads_id(gr_id):
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
