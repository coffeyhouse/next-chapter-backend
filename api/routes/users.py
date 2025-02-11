# api/routes/users.py

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime

from core.sa.database import get_db
from core.sa.repositories.user import UserRepository
from api.schemas.user import User, UserList
from api.schemas.book import BookList

router = APIRouter(prefix="/users", tags=["users"])

@router.get("", response_model=UserList)
def get_users(
    query: Optional[str] = Query(None, description="Search users by name"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get a paginated list of users with optional name search.
    
    Args:
        query: Optional search string to filter users by name
        page: Page number (1-based)
        size: Number of items per page
        db: Database session
    
    Returns:
        UserList containing paginated users with basic information
    """
    repo = UserRepository(db)
    
    # Calculate offset for pagination
    offset = (page - 1) * size
    
    # Get users with pagination
    users = repo.search_users(query=query, limit=size)
    
    # Get total count for pagination
    total = len(users)
    
    # Create response with just the basic user information
    response = {
        "items": [
            {
                "id": user.id,
                "name": user.name
            }
            for user in users
        ],
        "total": total,
        "page": page,
        "size": size
    }
    
    return UserList(**response)

@router.get("/{user_id}/books", response_model=BookList)
def get_user_books(
    user_id: int,
    status: Optional[List[str]] = Query(["completed", "reading"], description="Book statuses to include"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get a paginated list of books that a user has read or is reading.
    
    Args:
        user_id: The ID of the user
        status: List of statuses to include (default: ["completed", "reading"])
        page: Page number (1-based)
        size: Number of items per page
        db: Database session
    
    Returns:
        BookList containing the user's books with status information
    """
    repo = UserRepository(db)
    
    # Check if user exists
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Calculate offset for pagination
    offset = (page - 1) * size
    
    # Get user's books
    books = repo.get_user_books_by_statuses(
        user_id=user_id,
        statuses=status,
        limit=size,
        offset=offset
    )
    
    # Get total count
    total = repo.count_user_books_by_statuses(user_id=user_id, statuses=status)
    
    # Create response with book information
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
                ],
                "user_status": next((
                    {
                        "status": bu.status,
                        "finished_at": bu.finished_at,
                        "source": bu.source
                    }
                    for bu in book.book_users
                    if bu.user_id == user_id
                    and bu.status in status
                ), None)
            }
            for book in books
        ],
        "total": total,
        "page": page,
        "size": size
    }
    
    return BookList(**response)