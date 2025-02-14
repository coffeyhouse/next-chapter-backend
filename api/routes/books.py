# api/routes/books.py

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from core.sa.database import get_db
from core.sa.repositories.book import BookRepository
from api.schemas.book import Book, BookList, SeriesList
from api.schemas.user import BookUserCreate, BookUserUpdate

router = APIRouter(prefix="/books", tags=["books"])

@router.get("", response_model=BookList)
def get_books(
    query: Optional[str] = Query(None, description="Search books by title"),
    source: Optional[str] = Query(None, description="Filter books by source"),
    sort: str = Query("goodreads_votes", description="Sort field (goodreads_votes, goodreads_rating, title, published_date)"),
    order: str = Query("desc", description="Sort order (asc or desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get a paginated list of books with optional title search and source filter.
    
    Args:
        query: Optional search string to filter books by title
        source: Optional source to filter books
        sort: Field to sort by (goodreads_votes, goodreads_rating, title, published_date)
        order: Sort order (asc or desc)
        page: Page number (1-based)
        size: Number of items per page
        db: Database session
    
    Returns:
        BookList containing paginated books with basic information
    """
    # Validate sort field
    valid_sort_fields = ["goodreads_votes", "goodreads_rating", "title", "published_date"]
    if sort not in valid_sort_fields:
        raise HTTPException(status_code=400, detail=f"Invalid sort field. Must be one of: {', '.join(valid_sort_fields)}")
    
    # Validate sort order
    if order not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Invalid sort order. Must be 'asc' or 'desc'")
    
    repo = BookRepository(db)
    
    # Calculate offset for pagination
    offset = (page - 1) * size
    
    # Get books with search and source filter
    books = repo.search_books(
        query=query,
        source=source,
        sort_field=sort,
        sort_order=order,
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
                "goodreads_id": book.goodreads_id,
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

@router.get("/series", response_model=SeriesList)
def get_series(
    query: Optional[str] = Query(None, description="Search series by title"),
    user_id: Optional[int] = Query(None, description="Optional user ID to include read counts. If not provided, read_count will be 0"),
    sort: str = Query("book_count", description="Sort by 'book_count' or 'read_count'"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get a paginated list of series with book counts.
    
    Args:
        query: Optional search string to filter series by title
        user_id: Optional user ID to get read counts for. If provided, each series will include
                how many books in that series the user has completed. If not provided, read_count
                will be 0 for all series.
        sort: Sort by 'book_count' (default) or 'read_count'
        page: Page number (1-based)
        size: Number of items per page
        db: Database session
    
    Returns:
        SeriesList containing paginated series with:
        - Total number of books in each series (book_count)
        - Number of books the user has read in each series (read_count, 0 if no user_id provided)
        - Basic series information (goodreads_id, title)
    
    Raises:
        HTTPException: If sort parameter is invalid
    """
    if sort not in ["book_count", "read_count"]:
        raise HTTPException(status_code=400, detail="Sort must be either 'book_count' or 'read_count'")
    
    repo = BookRepository(db)
    
    # Calculate offset for pagination
    offset = (page - 1) * size
    
    # Get series with book counts
    series_with_counts = repo.get_series_with_counts(
        query=query,
        user_id=user_id,
        sort_by=sort,
        limit=size,
        offset=offset
    )
    
    # Get total count
    total = repo.count_series(query=query)
    
    # Create response
    response = {
        "items": [
            {
                "goodreads_id": series.goodreads_id,
                "title": series.title,
                "book_count": total_count,
                "read_count": read_count
            }
            for series, total_count, read_count in series_with_counts
        ],
        "total": total,
        "page": page,
        "size": size
    }
    
    return SeriesList(**response)

@router.get("/{work_id}", response_model=Book)
def get_book_by_work_id(
    work_id: str,
    user_id: Optional[int] = Query(None, description="Optional user ID to include read status and wanted status"),
    db: Session = Depends(get_db)
):
    """
    Get a single book by its work ID.
    
    Args:
        work_id: The work ID of the book to retrieve
        user_id: Optional user ID to include read status and wanted status information
        db: Database session
    
    Returns:
        Book object with full information including:
        - Basic book details (title, work_id, etc.)
        - Authors and series information
        - Description and image URL
        - Published status
        - User read status (if user_id provided)
        - Whether the book is wanted by the user (if user_id provided)
        - Similar books
        
    Raises:
        HTTPException: If the book is not found
    """
    repo = BookRepository(db)
    
    book = repo.get_by_work_id(work_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book with work_id {work_id} not found")
    
    # Create response with all requested information
    response = {
        "title": book.title,
        "goodreads_id": book.goodreads_id,
        "work_id": book.work_id,
        "source": book.source,
        "pages": book.pages,
        "goodreads_rating": book.goodreads_rating,
        "goodreads_votes": book.goodreads_votes,
        "published_date": book.published_date,
        "published_state": book.published_state,
        "description": book.description,
        "image_url": book.image_url,
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
        ],
        "user_status": next((
            {
                "status": bu.status,
                "started_at": bu.started_at,
                "finished_at": bu.finished_at,
                "source": bu.source
            }
            for bu in book.book_users
            if bu.user_id == user_id
        ), None) if user_id else None,
        "similar_books": [
            {
                "title": similar.similar_book.title,
                "work_id": similar.similar_book.work_id,
                "goodreads_rating": similar.similar_book.goodreads_rating,
                "goodreads_votes": similar.similar_book.goodreads_votes,
                "authors": [
                    {
                        "goodreads_id": ba.author.goodreads_id,
                        "name": ba.author.name
                    }
                    for ba in similar.similar_book.book_authors
                    if ba.role == "Author"
                ]
            }
            for similar in book.similar_to
        ],
        "wanted": next((
            {
                "source": bw.source,
                "created_at": bw.created_at
            }
            for bw in book.book_wanted
            if bw.user_id == user_id
        ), None) if user_id else None
    }
    
    return Book(**response)

@router.post("/{work_id}/status", response_model=Book)
def update_book_status(
    work_id: str,
    user_id: int = Query(..., description="ID of the user updating the status"),
    status: str = Query(..., description="Reading status (reading, completed)"),
    source: Optional[str] = Query(None, description="Source of the book (e.g., library, kindle)"),
    started_at: Optional[str] = Query(None, description="When the user started reading (ISO format). Use empty string to remove."),
    finished_at: Optional[str] = Query(None, description="When the user finished reading (ISO format). Use empty string to remove."),
    db: Session = Depends(get_db)
):
    """
    Update a book's reading status for a user.
    
    Args:
        work_id: The work ID of the book
        user_id: ID of the user updating the status
        status: Reading status (reading, completed)
        source: Optional source of the book
        started_at: Optional start date (ISO format). Use empty string to remove.
        finished_at: Optional finish date (ISO format). Use empty string to remove.
        db: Database session
    
    Returns:
        Updated book information including user's reading status
    """
    # Validate status
    valid_statuses = ["reading", "completed"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    repo = BookRepository(db)
    
    # Get the book first to ensure it exists
    book = repo.get_by_work_id(work_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book with work_id {work_id} not found")
    
    # Process dates - convert empty strings to None and parse valid dates
    try:
        started_at_date = None if started_at == "" else (datetime.fromisoformat(started_at) if started_at else None)
        finished_at_date = None if finished_at == "" else (datetime.fromisoformat(finished_at) if finished_at else None)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format (e.g., 2024-02-13T12:00:00)")
    
    # Update the book status
    book_user = repo.update_book_status(
        user_id=user_id,
        work_id=work_id,
        status=status,
        source=source,
        started_at=started_at_date,
        finished_at=finished_at_date,
        update_none=True  # Indicate that None values should be applied
    )
    
    if not book_user:
        raise HTTPException(
            status_code=500,
            detail="Failed to update book status"
        )
    
    # Return the updated book with user status
    return Book(
        title=book.title,
        goodreads_id=book.goodreads_id,
        work_id=book.work_id,
        source=book.source,
        pages=book.pages,
        goodreads_rating=book.goodreads_rating,
        goodreads_votes=book.goodreads_votes,
        published_date=book.published_date,
        published_state=book.published_state,
        description=book.description,
        image_url=book.image_url,
        authors=[
            {
                "goodreads_id": ba.author.goodreads_id,
                "name": ba.author.name
            }
            for ba in book.book_authors
            if ba.role == "Author"
        ],
        series=[
            {
                "goodreads_id": bs.series.goodreads_id,
                "title": bs.series.title,
                "order": bs.series_order
            }
            for bs in book.book_series
        ],
        user_status={
            "status": book_user.status,
            "started_at": book_user.started_at,
            "finished_at": book_user.finished_at,
            "source": book_user.source
        }
    )

@router.delete("/{work_id}/status", status_code=204)
def delete_book_status(
    work_id: str,
    user_id: int = Query(..., description="ID of the user removing the status"),
    db: Session = Depends(get_db)
):
    """
    Remove a book's reading status for a user.
    
    Args:
        work_id: The work ID of the book
        user_id: ID of the user removing the status
        db: Database session
    
    Returns:
        204 No Content on success
        
    Raises:
        HTTPException: If the book is not found or the status couldn't be deleted
    """
    repo = BookRepository(db)
    
    # Get the book first to ensure it exists
    book = repo.get_by_work_id(work_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book with work_id {work_id} not found")
    
    # Delete the status
    if not repo.delete_book_status(user_id=user_id, work_id=work_id):
        raise HTTPException(
            status_code=404,
            detail="No status found for this book and user"
        )

@router.patch("/{work_id}/status", response_model=Book)
def patch_book_status(
    work_id: str,
    user_id: int = Query(..., description="ID of the user updating the status"),
    status: Optional[str] = Query(None, description="Reading status (reading, completed). Use empty string to remove."),
    source: Optional[str] = Query(None, description="Source of the book (e.g., library, kindle). Use empty string to remove."),
    started_at: Optional[str] = Query(None, description="When the user started reading (ISO format). Use empty string to remove."),
    finished_at: Optional[str] = Query(None, description="When the user finished reading (ISO format). Use empty string to remove."),
    db: Session = Depends(get_db)
):
    """
    Update specific fields of a book's reading status for a user.
    Only provided fields will be updated.
    Use empty string to explicitly set a field to null.
    
    Args:
        work_id: The work ID of the book
        user_id: ID of the user updating the status
        status: Optional reading status (reading, completed). Use empty string to remove.
        source: Optional source of the book. Use empty string to remove.
        started_at: Optional start date (ISO format). Use empty string to remove.
        finished_at: Optional finish date (ISO format). Use empty string to remove.
        db: Database session
    
    Returns:
        Updated book information including user's reading status
        
    Raises:
        HTTPException: If the book is not found, the status is invalid,
                      or the status update fails
    """
    repo = BookRepository(db)
    
    # Get the book first to ensure it exists
    book = repo.get_by_work_id(work_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book with work_id {work_id} not found")
    
    # Process dates - convert empty strings to None and parse valid dates
    try:
        started_at_date = None if started_at == "" else (datetime.fromisoformat(started_at) if started_at else None)
        finished_at_date = None if finished_at == "" else (datetime.fromisoformat(finished_at) if finished_at else None)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format (e.g., 2024-02-13T12:00:00)")
    
    # Process other fields - convert empty strings to None
    status_value = None if status == "" else status
    source_value = None if source == "" else source
    
    # Validate status if provided and not being removed
    if status_value is not None:
        valid_statuses = ["reading", "completed"]
        if status_value not in valid_statuses:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
    
    # Update the book status
    book_user = repo.update_book_status(
        user_id=user_id,
        work_id=work_id,
        status=status_value,
        source=source_value,
        started_at=started_at_date,
        finished_at=finished_at_date,
        update_none=True  # Indicate that None values should be applied
    )
    
    if not book_user:
        raise HTTPException(
            status_code=404,
            detail="No status found for this book and user"
        )
    
    # Return the updated book with user status
    return Book(
        title=book.title,
        goodreads_id=book.goodreads_id,
        work_id=book.work_id,
        source=book.source,
        pages=book.pages,
        goodreads_rating=book.goodreads_rating,
        goodreads_votes=book.goodreads_votes,
        published_date=book.published_date,
        published_state=book.published_state,
        description=book.description,
        image_url=book.image_url,
        authors=[
            {
                "goodreads_id": ba.author.goodreads_id,
                "name": ba.author.name
            }
            for ba in book.book_authors
            if ba.role == "Author"
        ],
        series=[
            {
                "goodreads_id": bs.series.goodreads_id,
                "title": bs.series.title,
                "order": bs.series_order
            }
            for bs in book.book_series
        ],
        user_status={
            "status": book_user.status,
            "started_at": book_user.started_at,
            "finished_at": book_user.finished_at,
            "source": book_user.source
        }
    )

@router.get("/author/{goodreads_id}", response_model=BookList)
def get_author_books(
    goodreads_id: str,
    user_id: Optional[int] = Query(None, description="Optional user ID to include read status and wanted status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get all books by an author, sorted by publication date.
    
    Args:
        goodreads_id: The Goodreads ID of the author
        user_id: Optional user ID to include read status and wanted status
        page: Page number (1-based)
        size: Number of items per page
        db: Database session
    
    Returns:
        BookList containing paginated books with:
        - Basic book information
        - Author information
        - Series information
        - User read status (if user_id provided)
        - Whether the book is wanted by the user (if user_id provided)
        
    Raises:
        HTTPException: If the author is not found
    """
    repo = BookRepository(db)
    
    # Calculate offset for pagination
    offset = (page - 1) * size
    
    # Get books by author with optional user status
    books = repo.get_books_by_author(
        author_id=goodreads_id,
        user_id=user_id,
        limit=size,
        offset=offset
    )
    
    # Get total count
    total = repo.count_books_by_author(author_id=goodreads_id)
    
    # Create response
    response = {
        "items": [
            {
                "title": book.title,
                "goodreads_id": book.goodreads_id,
                "work_id": book.work_id,
                "source": book.source,
                "pages": book.pages,
                "goodreads_rating": book.goodreads_rating,
                "goodreads_votes": book.goodreads_votes,
                "published_date": book.published_date,
                "published_state": book.published_state,
                "description": book.description,
                "image_url": book.image_url,
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
                ],
                "user_status": next((
                    {
                        "status": bu.status,
                        "started_at": bu.started_at,
                        "finished_at": bu.finished_at,
                        "source": bu.source
                    }
                    for bu in book.book_users
                    if bu.user_id == user_id
                ), None) if user_id else None,
                "wanted": next((
                    {
                        "source": bw.source,
                        "created_at": bw.created_at
                    }
                    for bw in book.book_wanted
                    if bw.user_id == user_id
                ), None) if user_id else None
            }
            for book in books
        ],
        "total": total,
        "page": page,
        "size": size
    }
    
    return BookList(**response)