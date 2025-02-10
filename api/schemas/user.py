# api/schemas/user.py

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from .book import BookSearch

# Base schemas
class UserBase(BaseModel):
    """Base schema for user data."""
    name: str

class BookStatusBase(BaseModel):
    """Base schema for book status data."""
    status: str = Field(..., description="Book status (reading, completed, want_to_read)")
    source: Optional[str] = Field(None, description="Source of the status update")
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

# Create/Update schemas
class UserCreate(UserBase):
    """Schema for creating a new user."""
    pass

class UserUpdate(UserBase):
    """Schema for updating a user."""
    pass

class BookStatusCreate(BookStatusBase):
    """Schema for creating/updating a book status."""
    pass

class BookStatusUpdate(BookStatusBase):
    """Schema for updating a book status."""
    pass

# Response schemas
class UserResponse(UserBase):
    """Basic user response schema."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserDetail(UserResponse):
    """Detailed user response schema with relationships."""
    books: List[BookSearch]

    class Config:
        from_attributes = True

class BookStatusResponse(BookStatusBase):
    """Schema for book status responses."""
    user_id: int
    work_id: str
    book: BookSearch
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserBookStats(BaseModel):
    """Schema for user reading statistics."""
    total_books: int
    books_read_this_year: int
    currently_reading: int
    want_to_read: int
    average_rating: Optional[float] = None
    favorite_genres: List[str]
    reading_pace: Optional[float] = Field(None, description="Average books per month")
    total_pages_read: Optional[int] = None

    class Config:
        from_attributes = True 