# api/routes/books.py

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.sa.database import get_db
from core.sa.repositories.book import BookRepository
from api.schemas.book import Book, BookList

router = APIRouter(prefix="/books", tags=["books"])

@router.get("", response_model=BookList)
def get_books(
    query: Optional[str] = Query(None, description="Search books by title"),
    source: Optional[str] = Query(None, description="Filter books by source"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get a paginated list of books with optional title search and source filter.
    
    Args:
        query: Optional search string to filter books by title
        source: Optional source to filter books
        page: Page number (1-based)
        size: Number of items per page
        db: Database session
    
    Returns:
        BookList containing paginated books with basic information
    """
    repo = BookRepository(db)
    
    # Calculate offset for pagination
    offset = (page - 1) * size
    
    # Get books with search and source filter
    books = repo.search_books(
        query=query,
        source=source,
        limit=size,
        offset=offset
    )
    
    # Get total count
    total = repo.count_books(query=query, source=source)
    
    # Create response with basic book information
    response = {
        "items": [
            {
                "title": book.title,
                "work_id": book.work_id,
                "source": book.source,
                "pages": book.pages,
                "goodreads_rating": book.goodreads_rating,
                "goodreads_votes": book.goodreads_votes,
                "published_date": book.published_date,
                "authors": [
                    {
                        "goodreads_id": ba.author.goodreads_id,
                        "name": ba.author.name
                    }
                    for ba in book.book_authors
                    if ba.role == "Author"
                ],
                "series": [
                    {
                        "goodreads_id": bs.series.goodreads_id,
                        "title": bs.series.title,
                        "order": bs.series_order
                    }
                    for bs in book.book_series
                ]
            }
            for book in books
        ],
        "total": total,
        "page": page,
        "size": size
    }
    
    return BookList(**response)