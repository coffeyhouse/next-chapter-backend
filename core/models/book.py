# core/models/book.py

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List
from enum import Enum

class ReadingStatus(str, Enum):
    READ = "read"
    READING = "reading"
    PLAN_TO_READ = "plan_to_read"
    NONE = "none"

class PublishedState(str, Enum):
    PUBLISHED = "published"
    UPCOMING = "upcoming"

class AuthorRole(str, Enum):
    AUTHOR = "Author"
    TRANSLATOR = "Translator"
    ILLUSTRATOR = "Illustrator"

class AuthorBase(BaseModel):
    goodreads_id: str
    name: str
    role: str

class SeriesBase(BaseModel):
    goodreads_id: str
    title: str
    order: Optional[float] = None

class GenreBase(BaseModel):
    name: str

class BookBase(BaseModel):
    """Base book model with common fields"""
    model_config = ConfigDict(from_attributes=True)

    goodreads_id: str
    work_id: str
    title: str
    published_date: Optional[datetime] = None
    published_state: Optional[PublishedState] = None
    language: Optional[str] = None
    pages: Optional[int] = None
    isbn: Optional[str] = None
    goodreads_rating: Optional[float] = None
    goodreads_votes: Optional[int] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    hidden: bool = False

class SimilarBook(BookBase):
    """Simplified book model for similar books list"""
    authors: List[AuthorBase]

class BookDetail(BookBase):
    """Detailed book model for single book view"""
    authors: List[AuthorBase]
    series: List[SeriesBase]
    genres: List[GenreBase]
    similar_books: List[SimilarBook]
    reading_status: ReadingStatus = ReadingStatus.NONE
    is_wanted: bool = False
    is_in_library: bool = False
    library_calibre_id: Optional[int] = None
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class BookListItem(BookBase):
    """Simplified book model for lists"""
    authors: List[AuthorBase]
    series: Optional[SeriesBase] = None
    reading_status: ReadingStatus = ReadingStatus.NONE
    is_wanted: bool = False
    is_in_library: bool = False

class UpdateReadingStatus(BaseModel):
    """Model for updating a book's reading status"""
    status: ReadingStatus
    user_id: int

class UpdateWantedStatus(BaseModel):
    """Model for updating a book's wanted status"""
    is_wanted: bool
    user_id: int