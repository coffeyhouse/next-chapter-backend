from typing import List, Optional
from fastapi import APIRouter, Depends, Query

from core.models.book import (
    BookDetail, BookListItem,
    UpdateReadingStatus, UpdateWantedStatus
)
from core.services.book_service import BookService
from core.database import GoodreadsDB

router = APIRouter(prefix="/books", tags=["books"])

# Dependency to get database instance
async def get_db():
    db = GoodreadsDB()
    try:
        yield db
    finally:
        pass  # Add cleanup if needed

# Dependency to get BookService instance
async def get_book_service(db: GoodreadsDB = Depends(get_db)) -> BookService:
    return BookService(db)

@router.get("/{goodreads_id}", response_model=BookDetail)
async def get_book(
    goodreads_id: str,
    user_id: Optional[int] = Query(None, description="Optional user ID for personalized data"),
    book_service: BookService = Depends(get_book_service)
):
    """
    Get detailed information about a specific book.
    Includes all relationships (authors, series, genres) and user-specific data if user_id provided.
    """
    return await book_service.get_book_detail(goodreads_id, user_id)

@router.post("/{goodreads_id}/status", response_model=BookDetail)
async def update_book_status(
    goodreads_id: str,
    update: UpdateReadingStatus,
    book_service: BookService = Depends(get_book_service)
):
    """
    Update the reading status of a book for a specific user.
    Status can be: read, reading, plan_to_read, or none
    """
    return await book_service.update_reading_status(goodreads_id, update)

@router.post("/{goodreads_id}/wanted", response_model=BookDetail)
async def update_wanted_status(
    goodreads_id: str,
    update: UpdateWantedStatus,
    book_service: BookService = Depends(get_book_service)
):
    """
    Update whether a book is wanted by a specific user
    """
    return await book_service.update_wanted_status(goodreads_id, update)

@router.get("/search", response_model=List[BookListItem])
async def search_books(
    query: str = Query(..., min_length=2, description="Search query string"),
    user_id: Optional[int] = Query(None, description="Optional user ID for personalized data"),
    book_service: BookService = Depends(get_book_service)
):
    """
    Search for books by title, author, or ISBN.
    Includes user-specific data if user_id provided.
    """
    return await book_service.search_books(query, user_id)

@router.get("/", response_model=List[BookListItem])
async def get_all_books(
    limit: int = Query(50, ge=1, le=100, description="Number of books to return"),
    offset: int = Query(0, ge=0, description="Number of books to skip"),
    source: Optional[str] = Query(None, description="Filter by source (e.g. 'library')"),
    sort_by: str = Query("title", description="Field to sort by"),
    sort_order: str = Query("asc", description="Sort direction ('asc' or 'desc')"),
    user_id: Optional[int] = Query(None, description="Optional user ID for personalized data"),
    book_service: BookService = Depends(get_book_service)
):
    """
    Get all books with pagination, sorting, and filtering options.
    Includes user-specific data if user_id is provided.
    """
    return await book_service.get_all_books(
        limit=limit,
        offset=offset,
        source=source,
        sort_by=sort_by,
        sort_order=sort_order,
        user_id=user_id
    )