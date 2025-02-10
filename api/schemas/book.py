# api/schemas/book.py

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

# Base schemas
class BookBase(BaseModel):
    """Base schema for book data."""
    title: str
    published_date: Optional[datetime] = None
    language: Optional[str] = None
    pages: Optional[int] = None
    isbn: Optional[str] = None
    goodreads_rating: Optional[float] = None
    goodreads_votes: Optional[int] = None
    description: Optional[str] = None
    image_url: Optional[str] = None

class LibraryEntryBase(BaseModel):
    """Base schema for library entry data."""
    title: Optional[str] = None
    calibre_id: Optional[int] = None
    isbn: Optional[str] = None

# Create/Update schemas
class BookCreate(BookBase):
    """Schema for creating a new book."""
    goodreads_id: str
    work_id: str
    genre_ids: Optional[List[int]] = None
    series_ids: Optional[List[str]] = None
    author_ids: Optional[List[str]] = None

class BookUpdate(BookBase):
    """Schema for updating a book."""
    hidden: Optional[bool] = None

class LibraryEntryCreate(LibraryEntryBase):
    """Schema for creating a new library entry."""
    pass

class LibraryEntryUpdate(LibraryEntryBase):
    """Schema for updating a library entry."""
    pass

# Response schemas
class AuthorBrief(BaseModel):
    """Brief author information for book responses."""
    goodreads_id: str
    name: str

    class Config:
        from_attributes = True

class GenreBrief(BaseModel):
    """Brief genre information for book responses."""
    id: int
    name: str

    class Config:
        from_attributes = True

class SeriesBrief(BaseModel):
    """Brief series information for book responses."""
    goodreads_id: str
    title: str

    class Config:
        from_attributes = True

class BookSearch(BaseModel):
    """Schema for book search results."""
    goodreads_id: str
    work_id: str
    title: str
    authors: List[AuthorBrief]
    goodreads_rating: Optional[float] = None
    image_url: Optional[str] = None

    class Config:
        from_attributes = True

class BookResponse(BookBase):
    """Basic book response schema."""
    goodreads_id: str
    work_id: str
    hidden: bool = False

    class Config:
        from_attributes = True

class BookDetail(BookResponse):
    """Detailed book response schema with relationships."""
    authors: List[AuthorBrief]
    genres: List[GenreBrief]
    series: List[SeriesBrief]

    class Config:
        from_attributes = True

class LibraryEntryResponse(LibraryEntryBase):
    """Schema for library entry responses."""
    id: int
    work_id: str
    goodreads_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 