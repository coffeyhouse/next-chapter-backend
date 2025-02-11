# api/schemas/book.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class AuthorBase(BaseModel):
    goodreads_id: str
    name: str
    
    model_config = ConfigDict(from_attributes=True)

class SeriesBase(BaseModel):
    goodreads_id: str
    title: str
    order: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)

class BookUserStatus(BaseModel):
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    source: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class BookBase(BaseModel):
    title: str
    work_id: str
    source: Optional[str] = None
    pages: Optional[int] = None
    goodreads_rating: Optional[float] = None
    goodreads_votes: Optional[int] = None
    published_date: Optional[datetime] = None
    authors: List[AuthorBase] = []
    series: List[SeriesBase] = []
    user_status: Optional[BookUserStatus] = None

class Book(BookBase):
    model_config = ConfigDict(from_attributes=True)

class BookList(BaseModel):
    items: List[Book]
    total: int
    page: int
    size: int
    
    model_config = ConfigDict(from_attributes=True)

# Keep other schemas for future use
class BookCreate(BookBase):
    authors: List[AuthorBase] = []
    genres: List["GenreBase"] = []

class BookUpdate(BaseModel):
    title: Optional[str] = None
    source: Optional[str] = None

class GenreBase(BaseModel):
    id: int
    name: str
    
    model_config = ConfigDict(from_attributes=True)