# api/routes/users.py

from typing import List, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from datetime import datetime

from core.sa.database import get_db
from core.sa.repositories.user import UserRepository
from core.sa.models import Book, BookSeries, BookAuthor, Author, Series, UserSeriesSubscription
from api.schemas.user import (
    User, UserList, BookWantedCreate, BookWantedResponse,
    AuthorSubscriptionResponse, SeriesSubscriptionResponse, SubscriptionList,
    SeparatedSubscriptionList, SubscriptionResponse, UnifiedSubscriptionList,
    SubscriptionTypeEnum
)
from api.schemas.book import BookList, GenreCountList

router = APIRouter(prefix="/users", tags=["users"])

@router.get("", response_model=UserList)
def get_users(
    query: Optional[str] = Query(None, description="Search users by name"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get a paginated list of users.
    
    Args:
        query: Optional search string to filter users by name
        page: Page number (1-based)
        size: Number of items per page
        db: Database session
    
    Returns:
        UserList containing paginated users with basic information
    """
    repo = UserRepository(db)
    
    # Get users with search filter
    users = repo.search_users(query=query, limit=size)
    
    # Create response with user information
    response = {
        "items": [
            {
                "id": user.id,
                "name": user.name,
                "created_at": user.created_at,
                "updated_at": user.updated_at
            }
            for user in users
        ],
        "total": len(users),
        "page": page,
        "size": size
    }
    
    return UserList(**response)

@router.get("/{user_id}/books", response_model=BookList)
def get_user_books(
    user_id: int,
    status: Optional[List[str]] = Query(["completed", "reading"], description="Book statuses to include"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get a paginated list of books that a user has read or is reading.
    
    Args:
        user_id: The ID of the user
        status: List of statuses to include (default: ["completed", "reading"])
        page: Page number (1-based)
        size: Number of items per page
        db: Database session
    
    Returns:
        BookList containing the user's books with status information
    """
    repo = UserRepository(db)
    
    # Check if user exists
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Calculate offset for pagination
    offset = (page - 1) * size
    
    # Get user's books
    books = repo.get_user_books_by_statuses(
        user_id=user_id,
        statuses=status,
        limit=size,
        offset=offset
    )
    
    # Get total count
    total = repo.count_user_books_by_statuses(user_id=user_id, statuses=status)
    
    # Create response with book information
    response = {
        "items": [
            {
                "title": book.title,
                "work_id": book.work_id,
                "source": book.source,
                "pages": book.pages,
                "goodreads_rating": book.goodreads_rating,
                "goodreads_votes": book.goodreads_votes,
                "published_date": book.published_date,
                "authors": [
                    {
                        "goodreads_id": ba.author.goodreads_id,
                        "name": ba.author.name
                    }
                    for ba in book.book_authors
                    if ba.role == "Author"
                ],
                "series": [
                    {
                        "goodreads_id": bs.series.goodreads_id,
                        "title": bs.series.title,
                        "order": bs.series_order
                    }
                    for bs in book.book_series
                ],
                "user_status": next((
                    {
                        "status": bu.status,
                        "finished_at": bu.finished_at,
                        "source": bu.source
                    }
                    for bu in book.book_users
                    if bu.user_id == user_id
                    and bu.status in status
                ), None)
            }
            for book in books
        ],
        "total": total,
        "page": page,
        "size": size
    }
    
    return BookList(**response)

@router.get("/{user_id}/books/similar", response_model=BookList)
def get_user_similar_books(
    user_id: int,
    min_count: int = Query(1, ge=1, description="Minimum number of times a book should appear as similar"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get a paginated list of books that are marked as similar to the user's read books.
    Books are ordered by how many times they appear as similar.
    
    Args:
        user_id: The ID of the user
        min_count: Minimum number of times a book should appear as similar
        page: Page number (1-based)
        size: Number of items per page
        db: Database session
    
    Returns:
        BookList containing similar books with their frequency count
    """
    repo = UserRepository(db)
    
    # Check if user exists
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Calculate offset for pagination
    offset = (page - 1) * size
    
    # Get similar books
    books_with_count = repo.get_similar_books_for_user_reads(
        user_id=user_id,
        min_count=min_count,
        limit=size,
        offset=offset
    )
    
    # Get total count
    total = repo.count_similar_books_for_user_reads(user_id=user_id, min_count=min_count)
    
    # Create response with book information
    response = {
        "items": [
            {
                "title": book.title,
                "goodreads_id": book.goodreads_id,
                "work_id": book.work_id,
                "source": book.source,
                "pages": book.pages,
                "goodreads_rating": book.goodreads_rating,
                "goodreads_votes": book.goodreads_votes,
                "published_date": book.published_date,
                "authors": [
                    {
                        "goodreads_id": ba.author.goodreads_id,
                        "name": ba.author.name
                    }
                    for ba in book.book_authors
                    if ba.role == "Author"
                ],
                "series": [
                    {
                        "goodreads_id": bs.series.goodreads_id,
                        "title": bs.series.title,
                        "order": bs.series_order
                    }
                    for bs in book.book_series
                ],
                "similar_count": count  # Number of times this book appears as similar
            }
            for book, count in books_with_count
        ],
        "total": total,
        "page": page,
        "size": size
    }
    
    return BookList(**response)

@router.get("/{user_id}/genres", response_model=GenreCountList)
def get_user_genre_counts(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get counts of genres from books the user has read, ordered by frequency.
    For each genre, includes the top 3 unread books by Goodreads votes.
    
    Args:
        user_id: The ID of the user
        db: Database session
    
    Returns:
        GenreCountList containing genre names, their counts, and top unread books
    """
    repo = UserRepository(db)
    
    # Check if user exists
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get genre counts with top unread books
    genre_data = repo.get_user_read_genre_counts(user_id=user_id)
    print("\nConstructing response...")
    
    # Create response
    response = {
        "items": [
            {
                "name": name,
                "count": count,
                "top_unread": [
                    {
                        "title": book.title,
                        "work_id": book.work_id,
                        "goodreads_rating": book.goodreads_rating,
                        "goodreads_votes": book.goodreads_votes,
                        "authors": [
                            {
                                "goodreads_id": ba.author.goodreads_id,
                                "name": ba.author.name
                            }
                            for ba in book.book_authors
                            if ba.role == "Author"
                        ],
                        "series": [
                            {
                                "goodreads_id": bs.series.goodreads_id,
                                "title": bs.series.title,
                                "order": bs.series_order
                            }
                            for bs in book.book_series
                        ]
                    }
                    for book in top_unread
                ]
            }
            for name, count, top_unread in genre_data
        ],
        "total": len(genre_data)
    }
    
    # Debug print the response
    for item in response["items"]:
        print(f"\nGenre: {item['name']} (count: {item['count']})")
        print(f"Number of top_unread books: {len(item['top_unread'])}")
        for book in item['top_unread']:
            print(f"  - {book['title']} (votes: {book['goodreads_votes']})")
            if book['authors']:
                print(f"    Authors: {', '.join(a['name'] for a in book['authors'])}")
            if book['series']:
                print(f"    Series: {', '.join(s['title'] for s in book['series'])}")
    
    return GenreCountList(**response)

@router.get("/{user_id}/books/recommended", response_model=BookList)
def get_user_recommended_books(
    user_id: int,
    days: Optional[int] = Query(None, ge=1, description="Only consider books read within this many days"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get a paginated list of recommended books based on the user's genre preferences.
    Books are scored based on how many times the user has read books in each genre.
    For example, if a user has read 20 'Fiction' books and 10 'Mystery' books,
    an unread book with both genres would get a score of 30.
    
    The response includes a breakdown of which genres contributed to each book's score.
    
    Args:
        user_id: The ID of the user
        days: Optional. If provided, only consider books read within this many days
        page: Page number (1-based)
        size: Number of items per page
        db: Database session
    
    Returns:
        BookList containing recommended books ordered by genre-based score
    """
    repo = UserRepository(db)
    
    # Check if user exists
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Calculate offset for pagination
    offset = (page - 1) * size
    
    # Get recommended books with their scores
    books_with_scores = repo.get_recommended_books(
        user_id=user_id,
        days=days,
        limit=size,
        offset=offset
    )
    
    # Create response with book information
    response = {
        "items": [
            {
                "title": book.title,
                "goodreads_id": book.goodreads_id,
                "work_id": book.work_id,
                "source": book.source,
                "pages": book.pages,
                "goodreads_rating": book.goodreads_rating,
                "goodreads_votes": book.goodreads_votes,
                "published_date": book.published_date,
                "authors": [
                    {
                        "goodreads_id": ba.author.goodreads_id,
                        "name": ba.author.name
                    }
                    for ba in book.book_authors
                    if ba.role == "Author"
                ],
                "series": [
                    {
                        "goodreads_id": bs.series.goodreads_id,
                        "title": bs.series.title,
                        "order": bs.series_order
                    }
                    for bs in book.book_series
                ],
                "similar_count": total_score,  # Total genre-based score
                "matched_genres": [  # Add breakdown of genre scores
                    {
                        "name": genre_name,
                        "score": genre_score
                    }
                    for genre_name, genre_score in genre_scores
                ],
                "wanted": next((
                    {
                        "source": bw.source,
                        "created_at": bw.created_at
                    }
                    for bw in book.book_wanted
                    if bw.user_id == user_id
                ), None)
            }
            for book, total_score, genre_scores in books_with_scores
        ],
        "total": len(books_with_scores),  # For now, just use the number of returned items
        "page": page,
        "size": size
    } 
    
    return BookList(**response)

@router.get("/{user_id}/books/on-deck", response_model=BookList)
def get_user_on_deck_books(
    user_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get a paginated list of books that are 'on deck' for the user to read next.
    Returns books in the following order:
    1. Books currently being read
    2. Next unread books in series where the user has read previous books
    
    Args:
        user_id: The ID of the user
        page: Page number (1-based)
        size: Number of items per page
        db: Database session
    
    Returns:
        BookList containing the user's on-deck books
    """
    repo = UserRepository(db)
    
    # Check if user exists
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Calculate offset for pagination
    offset = (page - 1) * size
    
    # Get on-deck books
    books = repo.get_on_deck_books(
        user_id=user_id,
        limit=size,
        offset=offset
    )
    
    # Create response with book information
    response = {
        "items": [
            {
                "title": book.title,
                "goodreads_id": book.goodreads_id,
                "work_id": book.work_id,
                "source": book.source,
                "pages": book.pages,
                "goodreads_rating": book.goodreads_rating,
                "goodreads_votes": book.goodreads_votes,
                "published_date": book.published_date,
                "authors": [
                    {
                        "goodreads_id": ba.author.goodreads_id,
                        "name": ba.author.name
                    }
                    for ba in book.book_authors
                    if ba.role == "Author"
                ],
                "series": [
                    {
                        "goodreads_id": bs.series.goodreads_id,
                        "title": bs.series.title,
                        "order": bs.series_order
                    }
                    for bs in book.book_series
                ],
                "user_status": next((
                    {
                        "status": bu.status,
                        "finished_at": bu.finished_at,
                        "source": bu.source
                    }
                    for bu in book.book_users
                    if bu.user_id == user_id
                ), None)
            }
            for book in books
        ],
        "total": len(books),  # For now, just use the number of returned items
        "page": page,
        "size": size
    }
    
    # Debug print the response
    print(f"\nFound {len(books)} on-deck books:")
    for book in books:
        status = next((bu.status for bu in book.book_users if bu.user_id == user_id), None)
        print(f"\n{book.title}")
        print(f"Status: {status}")
        if book.book_series:
            print("Series:")
            for bs in book.book_series:
                print(f"  - {bs.series.title} (order: {bs.series_order})")
    
    return BookList(**response)

@router.post("/{user_id}/books/wanted/{work_id}", response_model=BookWantedResponse)
def add_wanted_book(
    user_id: int,
    work_id: str,
    source: str = Query(..., description="Where the book will be acquired from (e.g., 'library', 'kindle', 'manual')"),
    db: Session = Depends(get_db)
):
    """
    Add a book to the user's wanted list.
    
    Args:
        user_id: The ID of the user
        work_id: The work ID of the book to add
        source: Where the book will be acquired from (required, e.g., 'library', 'kindle', 'manual')
        db: Database session
    
    Returns:
        The created BookWanted entry
        
    Raises:
        HTTPException: 
            - 404: If the user or book doesn't exist
            - 400: If the book is already in the wanted list
            - 422: If source parameter is missing
    """
    if not source:
        raise HTTPException(
            status_code=422,
            detail="source parameter is required. Must specify where the book will be acquired from (e.g., 'library', 'kindle', 'manual')"
        )
    
    repo = UserRepository(db)
    
    # Check if user exists
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        wanted = repo.add_wanted_book(
            user_id=user_id,
            work_id=work_id,
            source=source
        )
        if not wanted:
            raise HTTPException(
                status_code=404,
                detail=f"Book with work_id {work_id} not found"
            )
        return wanted
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{user_id}/books/wanted/{work_id}", status_code=204)
def remove_wanted_book(
    user_id: int,
    work_id: str,
    db: Session = Depends(get_db)
):
    """
    Remove a book from the user's wanted list.
    
    Args:
        user_id: The ID of the user
        work_id: The work ID of the book to remove
        db: Database session
    
    Returns:
        204 No Content on success
        
    Raises:
        HTTPException: If the user doesn't exist or the book wasn't in the wanted list
    """
    repo = UserRepository(db)
    
    # Check if user exists
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not repo.remove_wanted_book(user_id=user_id, work_id=work_id):
        raise HTTPException(
            status_code=404,
            detail=f"Book {work_id} not found in user's wanted list"
        )

@router.get("/{user_id}/books/wanted", response_model=BookList)
def get_wanted_books(
    user_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get a paginated list of books in the user's wanted list.
    
    Args:
        user_id: The ID of the user
        page: Page number (1-based)
        size: Number of items per page
        db: Database session
    
    Returns:
        BookList containing the user's wanted books with full information
    """
    repo = UserRepository(db)
    
    # Check if user exists
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Calculate offset for pagination
    offset = (page - 1) * size
    
    # Get wanted books
    wanted_books = repo.get_wanted_books(
        user_id=user_id,
        limit=size,
        offset=offset
    )
    
    # Create response
    response = {
        "items": [
            {
                "title": book.title,
                "goodreads_id": book.goodreads_id,
                "work_id": book.work_id,
                "source": book.source,
                "pages": book.pages,
                "goodreads_rating": book.goodreads_rating,
                "goodreads_votes": book.goodreads_votes,
                "published_date": book.published_date,
                "authors": [
                    {
                        "goodreads_id": ba.author.goodreads_id,
                        "name": ba.author.name
                    }
                    for ba in book.book_authors
                    if ba.role == "Author"
                ],
                "series": [
                    {
                        "goodreads_id": bs.series.goodreads_id,
                        "title": bs.series.title,
                        "order": bs.series_order
                    }
                    for bs in book.book_series
                ],
                "user_status": {
                    "status": "wanted",
                    "source": wanted.source,
                    "started_at": None,
                    "finished_at": None
                }
            }
            for wanted, book in wanted_books
        ],
        "total": len(wanted_books),  # For now, just use the number of returned items
        "page": page,
        "size": size
    }
    
    return BookList(**response)

@router.post("/{user_id}/subscriptions", response_model=SubscriptionResponse)
def create_subscription(
    user_id: int,
    type: SubscriptionTypeEnum = Query(..., description="Type of subscription ('author' or 'series')"),
    goodreads_id: str = Query(..., description="Goodreads ID of the author or series to subscribe to"),
    db: Session = Depends(get_db)
):
    """
    Create a new subscription to either an author or series.
    
    Args:
        user_id: The ID of the user
        type: Type of subscription ('author' or 'series')
        goodreads_id: Goodreads ID of the author or series
        db: Database session
    
    Returns:
        SubscriptionResponse containing the created subscription details
    """
    repo = UserRepository(db)
    
    # Check if user exists
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if type == SubscriptionTypeEnum.author:
        result = repo.subscribe_to_author(user_id=user_id, author_id=goodreads_id)
        author = repo.session.query(Author).filter(Author.goodreads_id == goodreads_id).first()
        if not author:
            raise HTTPException(status_code=404, detail="Author not found")
        return SubscriptionResponse(
            type=SubscriptionTypeEnum.author,
            author_goodreads_id=result.author_goodreads_id,
            author_name=author.name,
            user_id=result.user_id,
            created_at=result.created_at,
            updated_at=result.updated_at,
            deleted_at=result.deleted_at
        )
    elif type == SubscriptionTypeEnum.series:
        try:
            result = repo.subscribe_to_series(user_id=user_id, series_goodreads_id=goodreads_id)
        except ValueError as e:
            if "UNIQUE constraint failed" in str(e):
                # Try to restore if it exists but is soft-deleted
                restored = repo.restore_series_subscription(user_id=user_id, series_goodreads_id=goodreads_id)
                if not restored:
                    raise HTTPException(status_code=400, detail="Already subscribed to this series")
                # Get the subscription after restoration
                result = (
                    repo.session.query(UserSeriesSubscription)
                    .filter(
                        UserSeriesSubscription.user_id == user_id,
                        UserSeriesSubscription.series_goodreads_id == goodreads_id
                    )
                    .first()
                )
            else:
                raise HTTPException(status_code=400, detail=str(e))
                
        series = repo.session.query(Series).filter(Series.goodreads_id == goodreads_id).first()
        if not series:
            raise HTTPException(status_code=404, detail="Series not found")
        
        # Get the author information
        series_author_id = repo.get_series_author_id(series.goodreads_id)
        author = None
        if series_author_id:
            author = repo.session.query(Author).filter(Author.goodreads_id == series_author_id).first()
        
        return SubscriptionResponse(
            type=SubscriptionTypeEnum.series,
            author_goodreads_id=series_author_id,
            author_name=author.name if author else None,
            series_goodreads_id=result.series_goodreads_id,
            series_name=series.title,
            user_id=result.user_id,
            created_at=result.created_at,
            updated_at=result.updated_at,
            deleted_at=result.deleted_at
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid subscription type")

@router.delete("/{user_id}/subscriptions", status_code=204)
def delete_subscription(
    user_id: int,
    type: SubscriptionTypeEnum = Query(..., description="Type of subscription ('author' or 'series')"),
    goodreads_id: str = Query(..., description="Goodreads ID of the author or series to unsubscribe from"),
    hard_delete: bool = Query(False, description="If True, permanently deletes the subscription; if False, soft deletes it"),
    db: Session = Depends(get_db)
):
    """
    Delete a subscription to either an author or series.
    
    Args:
        user_id: The ID of the user
        type: Type of subscription ('author' or 'series')
        goodreads_id: Goodreads ID of the author or series
        hard_delete: If True, permanently deletes; if False, soft deletes
        db: Database session
    """
    repo = UserRepository(db)
    
    # Check if user exists
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if type == SubscriptionTypeEnum.author:
        repo.unsubscribe_from_author(
            user_id=user_id,
            author_id=goodreads_id,
            hard_delete=hard_delete
        )
    elif type == SubscriptionTypeEnum.series:
        repo.unsubscribe_from_series(
            user_id=user_id,
            series_goodreads_id=goodreads_id,
            hard_delete=hard_delete
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid subscription type")

@router.patch("/{user_id}/subscriptions/restore", response_model=SubscriptionResponse)
def restore_subscription(
    user_id: int,
    type: SubscriptionTypeEnum = Query(..., description="Type of subscription ('author' or 'series')"),
    goodreads_id: str = Query(..., description="Goodreads ID of the author or series to restore"),
    db: Session = Depends(get_db)
):
    """
    Restore a soft-deleted subscription to either an author or series.
    
    Args:
        user_id: The ID of the user
        type: Type of subscription ('author' or 'series')
        goodreads_id: Goodreads ID of the author or series
        db: Database session
    
    Returns:
        SubscriptionResponse containing the restored subscription details
    """
    repo = UserRepository(db)
    
    # Check if user exists
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if type == SubscriptionTypeEnum.author:
        result = repo.restore_author_subscription(user_id=user_id, author_id=goodreads_id)
        author = repo.session.query(Author).filter(Author.goodreads_id == goodreads_id).first()
        if not author:
            raise HTTPException(status_code=404, detail="Author not found")
        return SubscriptionResponse(
            type=SubscriptionTypeEnum.author,
            author_goodreads_id=result.author_goodreads_id,
            author_name=author.name,
            user_id=result.user_id,
            created_at=result.created_at,
            updated_at=result.updated_at,
            deleted_at=result.deleted_at
        )
    elif type == SubscriptionTypeEnum.series:
        result = repo.restore_series_subscription(user_id=user_id, series_goodreads_id=goodreads_id)
        series = repo.session.query(Series).filter(Series.goodreads_id == goodreads_id).first()
        if not series:
            raise HTTPException(status_code=404, detail="Series not found")
        
        # Get the author information
        series_author_id = repo.get_series_author_id(series.goodreads_id)
        author = None
        if series_author_id:
            author = repo.session.query(Author).filter(Author.goodreads_id == series_author_id).first()
        
        return SubscriptionResponse(
            type=SubscriptionTypeEnum.series,
            author_goodreads_id=series_author_id,
            author_name=author.name if author else None,
            series_goodreads_id=result.series_goodreads_id,
            series_name=series.title,
            user_id=result.user_id,
            created_at=result.created_at,
            updated_at=result.updated_at,
            deleted_at=result.deleted_at
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid subscription type")

@router.get("/{user_id}/subscriptions", response_model=UnifiedSubscriptionList)
def get_subscriptions(
    user_id: int,
    type: Optional[str] = Query(
        None,
        description="Filter by subscription type",
        enum=["author", "series"]
    ),
    include_deleted: bool = Query(False, description="Whether to include soft-deleted subscriptions"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get a list of user's subscriptions, optionally filtered by type.
    
    Args:
        user_id: The ID of the user
        type: Optional filter for subscription type ('author' or 'series')
        include_deleted: Whether to include soft-deleted subscriptions
        page: Page number (1-based)
        size: Number of items per page
        db: Database session
    
    Returns:
        UnifiedSubscriptionList containing subscriptions, optionally filtered by type
    """
    repo = UserRepository(db)
    
    # Check if user exists
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get subscriptions based on type filter
    all_subs = []
    
    # Get author subscriptions if no type filter or type is 'author'
    if not type or type == "author":
        author_subs = repo.get_author_subscriptions(
            user_id=user_id,
            include_deleted=include_deleted
        )
        for sub, author in author_subs:
            all_subs.append(SubscriptionResponse(
                type=SubscriptionTypeEnum.author,
                author_goodreads_id=sub.author_goodreads_id,
                author_name=author.name,
                user_id=sub.user_id,
                created_at=sub.created_at,
                updated_at=sub.updated_at,
                deleted_at=sub.deleted_at,
                series_books=None  # Not applicable for author subscriptions
            ))
    
    # Get series subscriptions if no type filter or type is 'series'
    if not type or type == "series":
        series_subs = repo.get_series_subscriptions(
            user_id=user_id,
            include_deleted=include_deleted
        )
        for sub, series in series_subs:
            # Get first three books in the series by release date
            series_books = repo.get_series_books(series.goodreads_id)
            
            # Get the author of the first book (assuming it's the series author)
            series_author_id = repo.get_series_author_id(series.goodreads_id)
            
            # Get the author's name from the Author table
            author = None
            if series_author_id:
                author = repo.session.query(Author).filter(Author.goodreads_id == series_author_id).first()
            
            all_subs.append(SubscriptionResponse(
                type=SubscriptionTypeEnum.series,
                author_goodreads_id=series_author_id,
                author_name=author.name if author else None,
                series_goodreads_id=sub.series_goodreads_id,
                series_name=series.title,
                user_id=sub.user_id,
                created_at=sub.created_at,
                updated_at=sub.updated_at,
                deleted_at=sub.deleted_at,
                series_books=[book.work_id for book in series_books] if series_books else None
            ))
    
    # Sort by created_at descending
    all_subs.sort(key=lambda x: x.created_at, reverse=True)
    
    # Apply pagination
    start_idx = (page - 1) * size
    end_idx = start_idx + size
    paginated_subs = all_subs[start_idx:end_idx]
    
    return UnifiedSubscriptionList(
        items=paginated_subs,
        total=len(all_subs),
        page=page,
        size=size
    )

@router.get("/{user_id}", response_model=User)
def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a user by their ID.
    
    Args:
        user_id: The ID of the user to retrieve
        db: Database session
    
    Returns:
        User object with basic information (id, name, timestamps)
        
    Raises:
        HTTPException: If the user is not found
    """
    repo = UserRepository(db)
    user = repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")
        
    return user

@router.get("/{user_id}/series/{series_id}/books", response_model=BookList)
def get_user_series_books(
    user_id: int,
    series_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all books in a series with their read status for a user.
    
    Args:
        user_id: The ID of the user
        series_id: The Goodreads ID of the series
        db: Database session
    
    Returns:
        BookList containing all books in the series with user's read status
    """
    repo = UserRepository(db)
    
    # Check if user exists
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get series books with user status
    books = repo.get_series_books_with_user_status(
        user_id=user_id,
        series_goodreads_id=series_id
    )
    
    # Create response with book information
    response = {
        "items": [
            {
                "title": book.title,
                "goodreads_id": book.goodreads_id,
                "work_id": book.work_id,
                "source": book.source,
                "pages": book.pages,
                "goodreads_rating": book.goodreads_rating,
                "goodreads_votes": book.goodreads_votes,
                "published_date": book.published_date,
                "authors": [
                    {
                        "goodreads_id": ba.author.goodreads_id,
                        "name": ba.author.name
                    }
                    for ba in book.book_authors
                    if ba.role == "Author"
                ],
                "series": [
                    {
                        "goodreads_id": bs.series.goodreads_id,
                        "title": bs.series.title,
                        "order": bs.series_order
                    }
                    for bs in book.book_series
                ],
                "user_status": next((
                    {
                        "status": bu.status,
                        "finished_at": bu.finished_at,
                        "source": bu.source
                    }
                    for bu in book.book_users
                    if bu.user_id == user_id
                ), None)
            }
            for book in books
        ],
        "total": len(books),
        "page": 1,  # Not paginated since we want all books in order
        "size": len(books)
    }
    
    return BookList(**response)

def get_series_books(self, series_id: str) -> List[Book]:
    """Get the first three books in a series by release date.
    
    Args:
        series_id: The Goodreads ID of the series
        
    Returns:
        List of up to three Book objects, ordered by published_date
    """
    return (
        self.session.query(Book)
        .join(BookSeries)
        .filter(BookSeries.series.has(goodreads_id=series_id))
        .order_by(Book.published_date)
        .limit(3)
        .all()
    )

def get_series_author_id(self, series_id: str) -> Optional[str]:
    """Get the Goodreads ID of the author of the first book in a series.
    
    Args:
        series_id: The Goodreads ID of the series
        
    Returns:
        The author's Goodreads ID if found, None otherwise
    """
    first_book = (
        self.session.query(Book)
        .join(BookSeries)
        .join(BookAuthor)
        .filter(
            BookSeries.series.has(goodreads_id=series_id),
            BookAuthor.role == "Author"
        )
        .order_by(Book.published_date)
        .first()
    )
    
    if first_book and first_book.book_authors:
        for ba in first_book.book_authors:
            if ba.role == "Author":
                return ba.author.goodreads_id
    return None