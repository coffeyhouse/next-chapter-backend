# api/schemas.py

from typing import List, Optional, TypeVar, Generic
from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime


# Reusable Schemas for Models
class AuthorSchema(BaseModel):
    goodreads_id: str
    name: str
    bio: Optional[str] = None
    image_url: Optional[str] = None
    role: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SeriesSchema(BaseModel):
    goodreads_id: str
    title: str
    order: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class GenreSchema(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class SimilarBookAuthorSchema(BaseModel):
    goodreads_id: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class SimilarBookSchema(BaseModel):
    goodreads_id: str
    work_id: str
    title: str
    goodreads_rating: Optional[float] = None
    goodreads_votes: Optional[int] = None
    hidden: bool
    user_status: Optional[str] = None
    wanted: bool = False
    authors: List[SimilarBookAuthorSchema] = []

    model_config = ConfigDict(from_attributes=True)


class BasicBookSchema(BaseModel):
    goodreads_id: str
    work_id: str
    title: str
    published_date: Optional[datetime] = None
    published_state: Optional[str] = None
    pages: Optional[int] = None
    goodreads_rating: Optional[float] = None
    goodreads_votes: Optional[int] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    source: Optional[str] = None
    hidden: bool
    hidden_reason: Optional[str] = None
    user_status: Optional[str] = None
    wanted: bool = False
    authors: List[AuthorSchema] = []
    genres: List[GenreSchema] = []
    series: List[SeriesSchema] = []

    model_config = ConfigDict(from_attributes=True)


class BookSchema(BasicBookSchema):
    similar_books: List[SimilarBookSchema] = []

    model_config = ConfigDict(from_attributes=True)


class UserSchema(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class BookUserSchema(BaseModel):  # Representation of user's relationship with a book (e.g., read status)
    work_id: str
    user_id: int
    status: str
    source: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    book: BasicBookSchema  # Change to BasicBookSchema since we don't need similar books here

    model_config = ConfigDict(from_attributes=True)


class BookWantedSchema(BaseModel):
    work_id: str
    user_id: int
    source: str
    book: BasicBookSchema  # Change to BasicBookSchema since we don't need similar books here

    model_config = ConfigDict(from_attributes=True)


class UserAuthorSubscriptionSchema(BaseModel):
    user_id: int
    author_goodreads_id: str
    author: AuthorSchema

    model_config = ConfigDict(from_attributes=True)


class UserSeriesSubscriptionSchema(BaseModel):
    user_id: int
    series_goodreads_id: str
    series: SeriesSchema
    first_three_book_ids: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)


# Input/Create Schemas (for POST/PUT requests)

class UserCreate(BaseModel):
    name: str


class BookStatusUpdate(BaseModel):
    status: str
    source: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    
    @field_validator('started_at', 'finished_at', mode='before')
    @classmethod
    def validate_dates(cls, value):
        # Convert empty strings to None
        if value == "":
            return None
        return value


class AuthorSubscriptionCreate(BaseModel):
    author_goodreads_id: str


class SeriesSubscriptionCreate(BaseModel):
    series_goodreads_id: str
    
DataT = TypeVar('DataT')

class PaginatedResponse(BaseModel, Generic[DataT]):
    """
    Generic schema for paginated API responses.
    """
    page: int
    total_pages: int
    total_items: int
    data: List[DataT]