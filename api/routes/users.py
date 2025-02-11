# api/routes/users.py

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime

from core.sa.database import get_db
from core.sa.repositories.user import UserRepository
from core.sa.repositories.book import BookRepository

router = APIRouter(prefix="/users", tags=["users"])