# api/routes/users.py

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime

from core.sa.database import get_db
from core.sa.repositories.user import UserRepository
from api.schemas.user import (
    User, UserList, BookWantedCreate, BookWantedResponse,
    AuthorSubscriptionResponse, SeriesSubscriptionResponse, SubscriptionList,
    SeparatedSubscriptionList
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

@router.post("/{user_id}/subscriptions/authors/{author_id}", response_model=AuthorSubscriptionResponse)
def subscribe_to_author(
    user_id: int,
    author_id: str,
    db: Session = Depends(get_db)
):
    """
    Subscribe a user to an author to receive updates about new books.
    
    Args:
        user_id: The ID of the user
        author_id: The Goodreads ID of the author
        db: Database session
    
    Returns:
        The created subscription with author information
        
    Raises:
        HTTPException: If the user doesn't exist, the author doesn't exist,
                      or the user is already subscribed
    """
    repo = UserRepository(db)
    
    # Check if user exists
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        subscription = repo.subscribe_to_author(user_id=user_id, author_goodreads_id=author_id)
        if not subscription:
            raise HTTPException(
                status_code=404,
                detail=f"Author with ID {author_id} not found"
            )
            
        # Get author name for response
        return {
            "goodreads_id": subscription.author_goodreads_id,
            "name": subscription.author.name,
            "user_id": subscription.user_id,
            "created_at": subscription.created_at,
            "updated_at": subscription.updated_at,
            "deleted_at": subscription.deleted_at
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{user_id}/subscriptions/series/{series_id}", response_model=SeriesSubscriptionResponse)
def subscribe_to_series(
    user_id: int,
    series_id: str,
    db: Session = Depends(get_db)
):
    """
    Subscribe a user to a series to receive updates about new books.
    
    Args:
        user_id: The ID of the user
        series_id: The Goodreads ID of the series
        db: Database session
    
    Returns:
        The created subscription with series information
        
    Raises:
        HTTPException: If the user doesn't exist, the series doesn't exist,
                      or the user is already subscribed
    """
    repo = UserRepository(db)
    
    # Check if user exists
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        subscription = repo.subscribe_to_series(user_id=user_id, series_goodreads_id=series_id)
        if not subscription:
            raise HTTPException(
                status_code=404,
                detail=f"Series with ID {series_id} not found"
            )
            
        # Get series title for response
        return {
            "goodreads_id": subscription.series_goodreads_id,
            "title": subscription.series.title,
            "user_id": subscription.user_id,
            "created_at": subscription.created_at,
            "updated_at": subscription.updated_at,
            "deleted_at": subscription.deleted_at
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{user_id}/subscriptions/authors/{author_id}", status_code=204)
def unsubscribe_from_author(
    user_id: int,
    author_id: str,
    hard_delete: bool = Query(False, description="Whether to permanently delete the subscription"),
    db: Session = Depends(get_db)
):
    """
    Unsubscribe a user from an author.
    
    Args:
        user_id: The ID of the user
        author_id: The Goodreads ID of the author
        hard_delete: If True, permanently deletes the subscription; if False, soft deletes
        db: Database session
    
    Returns:
        204 No Content on success
        
    Raises:
        HTTPException: If the user doesn't exist or wasn't subscribed to the author
    """
    repo = UserRepository(db)
    
    # Check if user exists
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not repo.unsubscribe_from_author(
        user_id=user_id,
        author_goodreads_id=author_id,
        hard_delete=hard_delete
    ):
        raise HTTPException(
            status_code=404,
            detail=f"No active subscription found for author {author_id}"
        )

@router.delete("/{user_id}/subscriptions/series/{series_id}", status_code=204)
def unsubscribe_from_series(
    user_id: int,
    series_id: str,
    hard_delete: bool = Query(False, description="Whether to permanently delete the subscription"),
    db: Session = Depends(get_db)
):
    """
    Unsubscribe a user from a series.
    
    Args:
        user_id: The ID of the user
        series_id: The Goodreads ID of the series
        hard_delete: If True, permanently deletes the subscription; if False, soft deletes
        db: Database session
    
    Returns:
        204 No Content on success
        
    Raises:
        HTTPException: If the user doesn't exist or wasn't subscribed to the series
    """
    repo = UserRepository(db)
    
    # Check if user exists
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not repo.unsubscribe_from_series(
        user_id=user_id,
        series_goodreads_id=series_id,
        hard_delete=hard_delete
    ):
        raise HTTPException(
            status_code=404,
            detail=f"No active subscription found for series {series_id}"
        )

@router.post("/{user_id}/subscriptions/authors/{author_id}/restore", response_model=AuthorSubscriptionResponse)
def restore_author_subscription(
    user_id: int,
    author_id: str,
    db: Session = Depends(get_db)
):
    """
    Restore a soft-deleted author subscription.
    
    Args:
        user_id: The ID of the user
        author_id: The Goodreads ID of the author
        db: Database session
    
    Returns:
        The restored subscription with author information
        
    Raises:
        HTTPException: If the user doesn't exist or the subscription wasn't found
    """
    repo = UserRepository(db)
    
    # Check if user exists
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not repo.restore_author_subscription(user_id=user_id, author_goodreads_id=author_id):
        raise HTTPException(
            status_code=404,
            detail=f"No soft-deleted subscription found for author {author_id}"
        )
        
    # Get restored subscription for response
    subscription, author = next(
        (sub, auth) for sub, auth in repo.get_author_subscriptions(
            user_id=user_id,
            include_deleted=True,
            limit=1
        )
        if sub.author_goodreads_id == author_id
    )
    
    return {
        "goodreads_id": subscription.author_goodreads_id,
        "name": author.name,
        "user_id": subscription.user_id,
        "created_at": subscription.created_at,
        "updated_at": subscription.updated_at,
        "deleted_at": subscription.deleted_at
    }

@router.post("/{user_id}/subscriptions/series/{series_id}/restore", response_model=SeriesSubscriptionResponse)
def restore_series_subscription(
    user_id: int,
    series_id: str,
    db: Session = Depends(get_db)
):
    """
    Restore a soft-deleted series subscription.
    
    Args:
        user_id: The ID of the user
        series_id: The Goodreads ID of the series
        db: Database session
    
    Returns:
        The restored subscription with series information
        
    Raises:
        HTTPException: If the user doesn't exist or the subscription wasn't found
    """
    repo = UserRepository(db)
    
    # Check if user exists
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not repo.restore_series_subscription(user_id=user_id, series_goodreads_id=series_id):
        raise HTTPException(
            status_code=404,
            detail=f"No soft-deleted subscription found for series {series_id}"
        )
        
    # Get restored subscription for response
    subscription, series = next(
        (sub, ser) for sub, ser in repo.get_series_subscriptions(
            user_id=user_id,
            include_deleted=True,
            limit=1
        )
        if sub.series_goodreads_id == series_id
    )
    
    return {
        "goodreads_id": subscription.series_goodreads_id,
        "title": series.title,
        "user_id": subscription.user_id,
        "created_at": subscription.created_at,
        "updated_at": subscription.updated_at,
        "deleted_at": subscription.deleted_at
    }

@router.get("/{user_id}/subscriptions", response_model=SeparatedSubscriptionList)
def get_user_subscriptions(
    user_id: int,
    include_deleted: bool = Query(False, description="Whether to include soft-deleted subscriptions"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get a paginated list of a user's subscriptions to authors and series.
    
    Args:
        user_id: The ID of the user
        include_deleted: Whether to include soft-deleted subscriptions
        page: Page number (1-based)
        size: Number of items per page
        db: Database session
    
    Returns:
        SeparatedSubscriptionList containing separate lists for author and series subscriptions
        
    Raises:
        HTTPException: If the user doesn't exist
    """
    repo = UserRepository(db)
    
    # Check if user exists
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Calculate offset for pagination
    offset = (page - 1) * size
    
    # Get author subscriptions
    author_subs = repo.get_author_subscriptions(
        user_id=user_id,
        include_deleted=include_deleted,
        limit=size,
        offset=offset
    )
    
    # Get series subscriptions
    series_subs = repo.get_series_subscriptions(
        user_id=user_id,
        include_deleted=include_deleted,
        limit=size,
        offset=offset
    )
    
    # Convert to response format
    author_items = [
        {
            "goodreads_id": sub.author_goodreads_id,
            "name": author.name,
            "user_id": sub.user_id,
            "created_at": sub.created_at,
            "updated_at": sub.updated_at,
            "deleted_at": sub.deleted_at
        }
        for sub, author in author_subs
    ]
    
    series_items = [
        {
            "goodreads_id": sub.series_goodreads_id,
            "title": series.title,
            "user_id": sub.user_id,
            "created_at": sub.created_at,
            "updated_at": sub.updated_at,
            "deleted_at": sub.deleted_at
        }
        for sub, series in series_subs
    ]
    
    return {
        "authors": author_items,
        "series": series_items,
        "total_authors": len(author_items),
        "total_series": len(series_items),
        "page": page,
        "size": size
    }

@router.get("/{user_id}/series/{series_id}/books", response_model=BookList)
def get_user_series_books(
    user_id: int,
    series_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all books in a series with their read status for a user.
    Books are ordered by their position in the series.
    
    Args:
        user_id: The ID of the user
        series_id: The Goodreads ID of the series
        db: Database session
    
    Returns:
        BookList containing all books in the series with user's read status
        
    Raises:
        HTTPException: If the user doesn't exist or the series doesn't exist
    """
    repo = UserRepository(db)
    
    # Check if user exists
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all books in the series with user status
    books = repo.get_series_books_with_user_status(
        user_id=user_id,
        series_goodreads_id=series_id
    )
    
    if not books:
        raise HTTPException(status_code=404, detail="Series not found or has no books")
    
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
                        "started_at": bu.started_at,
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
        "page": 1,  # No pagination needed as we want all books in the series
        "size": len(books)
    }
    
    return BookList(**response)

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