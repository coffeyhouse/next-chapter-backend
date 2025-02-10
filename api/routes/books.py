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

from api.schemas.book import (
    BookCreate,
    BookUpdate,
    BookResponse,
    BookDetail,
    BookSearch,
    LibraryEntryCreate,
    LibraryEntryUpdate,
    LibraryEntryResponse
)

router = APIRouter(prefix="/books", tags=["books"])

def get_book_repo(db: Session = Depends(get_db)) -> BookRepository:
    return BookRepository(db)

def get_genre_repo(db: Session = Depends(get_db)) -> GenreRepository:
    return GenreRepository(db)

def get_series_repo(db: Session = Depends(get_db)) -> SeriesRepository:
    return SeriesRepository(db)

def get_author_repo(db: Session = Depends(get_db)) -> AuthorRepository:
    return AuthorRepository(db)

def get_library_repo(db: Session = Depends(get_db)) -> LibraryRepository:
    return LibraryRepository(db)

@router.get("/{goodreads_id}", response_model=BookDetail)
async def get_book(
    goodreads_id: str,
    book_repo: BookRepository = Depends(get_book_repo)
):
    """Get a book by its Goodreads ID."""
    book = book_repo.get_by_goodreads_id(goodreads_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@router.get("/work/{work_id}", response_model=BookDetail)
async def get_book_by_work_id(
    work_id: str,
    book_repo: BookRepository = Depends(get_book_repo)
):
    """Get a book by its work ID."""
    book = book_repo.get_by_work_id(work_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@router.get("", response_model=List[BookSearch])
async def search_books(
    query: Optional[str] = Query(None, description="Search query for book titles. If not provided, returns all books."),
    limit: int = Query(20, ge=1, le=100),
    book_repo: BookRepository = Depends(get_book_repo)
):
    """Search for books by title. If no query is provided, returns all books up to the limit."""
    return book_repo.search_books(query, limit=limit)

@router.post("", response_model=BookDetail)
async def create_book(
    book: BookCreate,
    book_repo: BookRepository = Depends(get_book_repo),
    genre_repo: GenreRepository = Depends(get_genre_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    author_repo: AuthorRepository = Depends(get_author_repo)
):
    """Create a new book."""
    # Check if book already exists
    existing = book_repo.get_by_goodreads_id(book.goodreads_id)
    if existing:
        raise HTTPException(status_code=400, detail="Book already exists")

    # Create the book
    created = book_repo.create_book(
        goodreads_id=book.goodreads_id,
        work_id=book.work_id,
        title=book.title,
        published_date=book.published_date,
        language=book.language,
        pages=book.pages,
        isbn=book.isbn,
        goodreads_rating=book.goodreads_rating,
        goodreads_votes=book.goodreads_votes,
        description=book.description,
        image_url=book.image_url
    )

    # Add relationships if provided
    if book.genre_ids:
        for genre_id in book.genre_ids:
            genre = genre_repo.get_by_id(genre_id)
            if not genre:
                raise HTTPException(status_code=404, detail=f"Genre {genre_id} not found")
            book_repo.add_genre(created.work_id, genre_id)

    if book.series_ids:
        for series_id in book.series_ids:
            series = series_repo.get_by_goodreads_id(series_id)
            if not series:
                raise HTTPException(status_code=404, detail=f"Series {series_id} not found")
            book_repo.add_to_series(created.work_id, series_id)

    if book.author_ids:
        for author_id in book.author_ids:
            author = author_repo.get_by_goodreads_id(author_id)
            if not author:
                raise HTTPException(status_code=404, detail=f"Author {author_id} not found")
            book_repo.add_author(created.work_id, author_id)

    return created

@router.patch("/{goodreads_id}", response_model=BookDetail)
async def update_book(
    goodreads_id: str,
    book: BookUpdate,
    book_repo: BookRepository = Depends(get_book_repo)
):
    """Update a book's details."""
    existing = book_repo.get_by_goodreads_id(goodreads_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Book not found")

    updated = book_repo.update_book(
        goodreads_id=goodreads_id,
        title=book.title,
        published_date=book.published_date,
        language=book.language,
        pages=book.pages,
        isbn=book.isbn,
        goodreads_rating=book.goodreads_rating,
        goodreads_votes=book.goodreads_votes,
        description=book.description,
        image_url=book.image_url,
        hidden=book.hidden
    )
    return updated

@router.delete("/{goodreads_id}")
async def delete_book(
    goodreads_id: str,
    book_repo: BookRepository = Depends(get_book_repo)
):
    """Delete a book."""
    success = book_repo.delete_book(goodreads_id)
    if not success:
        raise HTTPException(status_code=404, detail="Book not found")
    return {"message": "Book deleted successfully"}

# Library entry routes
@router.get("/{goodreads_id}/library", response_model=List[LibraryEntryResponse])
async def get_library_entries(
    goodreads_id: str,
    book_repo: BookRepository = Depends(get_book_repo),
    library_repo: LibraryRepository = Depends(get_library_repo)
):
    """Get all library entries for a book."""
    book = book_repo.get_by_goodreads_id(goodreads_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    entries = library_repo.get_all_by_work_id(book.work_id)
    return entries

@router.post("/{goodreads_id}/library", response_model=LibraryEntryResponse)
async def create_library_entry(
    goodreads_id: str,
    entry: LibraryEntryCreate,
    book_repo: BookRepository = Depends(get_book_repo),
    library_repo: LibraryRepository = Depends(get_library_repo)
):
    """Create a new library entry for a book."""
    book = book_repo.get_by_goodreads_id(goodreads_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Check for duplicate Calibre ID if provided
    if entry.calibre_id:
        existing = library_repo.get_by_calibre_id(entry.calibre_id)
        if existing:
            raise HTTPException(status_code=400, detail="Calibre ID already exists")

    created = library_repo.create_entry(
        title=entry.title or book.title,
        work_id=book.work_id,
        calibre_id=entry.calibre_id,
        goodreads_id=goodreads_id,
        isbn=entry.isbn
    )
    return created

@router.patch("/library/{library_id}", response_model=LibraryEntryResponse)
async def update_library_entry(
    library_id: int,
    entry: LibraryEntryUpdate,
    library_repo: LibraryRepository = Depends(get_library_repo)
):
    """Update a library entry."""
    # Check for duplicate Calibre ID if provided
    if entry.calibre_id:
        existing = library_repo.get_by_calibre_id(entry.calibre_id)
        if existing and existing.id != library_id:
            raise HTTPException(status_code=400, detail="Calibre ID already exists")

    updated = library_repo.update_entry(
        library_id=library_id,
        title=entry.title,
        calibre_id=entry.calibre_id,
        isbn=entry.isbn
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Library entry not found")
    return updated

@router.delete("/library/{library_id}")
async def delete_library_entry(
    library_id: int,
    library_repo: LibraryRepository = Depends(get_library_repo)
):
    """Delete a library entry."""
    success = library_repo.delete_entry(library_id)
    if not success:
        raise HTTPException(status_code=404, detail="Library entry not found")
    return {"message": "Library entry deleted successfully"} 