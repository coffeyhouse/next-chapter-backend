# api/schemas/user.py
from datetime import datetime
from typing import Optional, List, Union
from pydantic import BaseModel, ConfigDict, model_validator
from enum import Enum

class UserBase(BaseModel):
    name: str

class User(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class UserList(BaseModel):
    items: List[User]
    total: int
    page: int
    size: int
    
    model_config = ConfigDict(from_attributes=True)

class UserCreate(UserBase):
    pass

class UserUpdate(UserBase):
    pass

class UserStats(BaseModel):
    total_books: int
    books_read_this_year: int
    currently_reading: int
    want_to_read: int
    average_rating: Optional[float] = None
    favorite_genres: List[str] = []
    reading_pace: Optional[float] = None
    total_pages_read: Optional[int] = None

class BookUserBase(BaseModel):
    work_id: str
    status: str
    source: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class BookUserCreate(BookUserBase):
    pass

class BookUserUpdate(BaseModel):
    status: Optional[str] = None
    source: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

class BookWantedCreate(BaseModel):
    work_id: str
    source: str
    
    model_config = ConfigDict(from_attributes=True)

class BookWantedResponse(BaseModel):
    work_id: str
    user_id: int
    source: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# Subscription Schemas
class SubscriptionBase(BaseModel):
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class AuthorSubscriptionResponse(SubscriptionBase):
    goodreads_id: str
    name: str
    user_id: int

class SeriesSubscriptionResponse(SubscriptionBase):
    goodreads_id: str
    title: str
    user_id: int

class SubscriptionList(BaseModel):
    items: List[Union[AuthorSubscriptionResponse, SeriesSubscriptionResponse]]
    total: int
    page: int
    size: int
    
    model_config = ConfigDict(from_attributes=True)

class SeparatedSubscriptionList(BaseModel):
    authors: List[AuthorSubscriptionResponse]
    series: List[SeriesSubscriptionResponse]
    total_authors: int
    total_series: int
    page: int
    size: int
    
    model_config = ConfigDict(from_attributes=True)

class SubscriptionTypeEnum(str, Enum):
    author = "author"
    series = "series"

class SubscriptionResponse(SubscriptionBase):
    type: SubscriptionTypeEnum
    author_goodreads_id: str
    author_name: Optional[str] = None
    series_goodreads_id: Optional[str] = None
    series_name: Optional[str] = None
    user_id: int
    series_books: Optional[List[str]] = None

class UnifiedSubscriptionList(BaseModel):
    items: List[SubscriptionResponse]
    total: int
    page: int
    size: int
    
    model_config = ConfigDict(from_attributes=True)