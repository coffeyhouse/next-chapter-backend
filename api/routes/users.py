# api/routes/users.py

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime

from core.sa.database import get_db
from core.sa.repositories.user import UserRepository
from core.sa.repositories.book import BookRepository

from api.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserDetail,
    BookStatusCreate,
    BookStatusUpdate,
    BookStatusResponse,
    UserBookStats
)

router = APIRouter(prefix="/users", tags=["users"])

def get_user_repo(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)

def get_book_repo(db: Session = Depends(get_db)) -> BookRepository:
    return BookRepository(db)

@router.get("/{user_id}", response_model=UserDetail)
async def get_user(
    user_id: int,
    user_repo: UserRepository = Depends(get_user_repo)
):
    """Get a user by their ID."""
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("", response_model=List[UserResponse])
async def search_users(
    query: Optional[str] = Query(None, description="Search query for usernames"),
    limit: int = Query(20, ge=1, le=100),
    user_repo: UserRepository = Depends(get_user_repo)
):
    """Search for users by name. If no query is provided, returns all users up to the limit."""
    return user_repo.search_users(query, limit=limit)

@router.post("", response_model=UserResponse)
async def create_user(
    user: UserCreate,
    user_repo: UserRepository = Depends(get_user_repo)
):
    """Create a new user."""
    try:
        return user_repo.create_user(name=user.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user: UserUpdate,
    user_repo: UserRepository = Depends(get_user_repo)
):
    """Update a user's details."""
    existing = user_repo.get_by_id(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user_repo.update_user(user_id=user_id, name=user.name)

@router.get("/{user_id}/books", response_model=List[BookStatusResponse])
async def get_user_books(
    user_id: int,
    status: Optional[str] = Query(None, description="Filter by book status (reading, completed, want_to_read)"),
    user_repo: UserRepository = Depends(get_user_repo)
):
    """Get all books associated with a user, optionally filtered by status."""
    user = user_repo.get_user_with_books(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    book_users = user.book_users
    if status:
        book_users = [bu for bu in book_users if bu.status == status]
    
    return book_users

@router.post("/{user_id}/books/{goodreads_id}", response_model=BookStatusResponse)
async def update_book_status(
    user_id: int,
    goodreads_id: str,
    status: BookStatusCreate,
    user_repo: UserRepository = Depends(get_user_repo),
    book_repo: BookRepository = Depends(get_book_repo)
):
    """Update or create a user's status for a book."""
    # Verify user exists
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify book exists
    book = book_repo.get_by_goodreads_id(goodreads_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Update the status
    book_user = user_repo.update_book_status(
        user_id=user_id,
        goodreads_id=goodreads_id,
        status=status.status,
        source=status.source,
        started_at=status.started_at,
        finished_at=status.finished_at
    )
    
    if not book_user:
        raise HTTPException(status_code=400, detail="Failed to update book status")
    
    return book_user

@router.delete("/{user_id}/books/{goodreads_id}")
async def remove_book_status(
    user_id: int,
    goodreads_id: str,
    user_repo: UserRepository = Depends(get_user_repo),
    book_repo: BookRepository = Depends(get_book_repo)
):
    """Remove a book status for a user."""
    # Verify user exists
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify book exists
    book = book_repo.get_by_goodreads_id(goodreads_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    success = user_repo.delete_book_status(user_id=user_id, work_id=book.work_id)
    if not success:
        raise HTTPException(status_code=404, detail="Book status not found")
    
    return {"message": "Book status removed successfully"}

@router.get("/{user_id}/stats", response_model=UserBookStats)
async def get_user_stats(
    user_id: int,
    user_repo: UserRepository = Depends(get_user_repo)
):
    """Get reading statistics for a user."""
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user_repo.get_user_stats(user_id) 