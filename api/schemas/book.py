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

class SeriesWithCount(BaseModel):
    goodreads_id: str
    title: str
    book_count: int
    read_count: int
    
    model_config = ConfigDict(from_attributes=True)

class SeriesList(BaseModel):
    items: List[SeriesWithCount]
    total: int
    page: int
    size: int
    
    model_config = ConfigDict(from_attributes=True)

class BookUserStatus(BaseModel):
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    source: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class SimilarBook(BaseModel):
    title: str
    work_id: str
    goodreads_rating: Optional[float] = None
    goodreads_votes: Optional[int] = None
    authors: List[AuthorBase] = []
    
    model_config = ConfigDict(from_attributes=True)

class BookWanted(BaseModel):
    source: Optional[str] = None
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class BookBase(BaseModel):
    title: str
    goodreads_id: Optional[str] = None
    work_id: str
    source: Optional[str] = None
    pages: Optional[int] = None
    goodreads_rating: Optional[float] = None
    goodreads_votes: Optional[int] = None
    published_date: Optional[datetime] = None
    published_state: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    authors: List[AuthorBase] = []
    series: List[SeriesBase] = []
    user_status: Optional[BookUserStatus] = None
    similar_books: Optional[List[SimilarBook]] = []
    similar_count: Optional[int] = None
    wanted: Optional[BookWanted] = None
    matched_genres: Optional[List["GenreScore"]] = None

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

class GenreBookSummary(BaseModel):
    title: str
    work_id: str
    goodreads_rating: Optional[float] = None
    goodreads_votes: Optional[int] = None
    authors: List[AuthorBase] = []
    series: List[SeriesBase] = []
    
    model_config = ConfigDict(from_attributes=True)

class GenreCount(BaseModel):
    name: str
    count: int
    top_unread: List[GenreBookSummary]
    
    model_config = ConfigDict(from_attributes=True)

class GenreCountList(BaseModel):
    items: List[GenreCount]
    total: int
    
    model_config = ConfigDict(from_attributes=True)

class GenreScore(BaseModel):
    name: str
    score: int
    
    model_config = ConfigDict(from_attributes=True)