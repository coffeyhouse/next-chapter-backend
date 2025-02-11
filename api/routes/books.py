# api/routes/books.py

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime

from core.sa.database import get_db
from core.sa.repositories.book import BookRepository
from core.sa.repositories.genre import GenreRepository
from core.sa.repositories.series import SeriesRepository
from core.sa.repositories.author import AuthorRepository
from core.sa.repositories.library import LibraryRepository


router = APIRouter(prefix="/books", tags=["books"])