# api/schemas/user.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class UserBase(BaseModel):
    name: str

class User(UserBase):
    id: int
    
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