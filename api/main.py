# api/main.py
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from core.sa.database import Database, get_db
from core.sa.repositories.user import UserRepository
from core.sa.repositories.book import BookRepository
from core.sa.repositories.author import AuthorRepository
from core.sa.repositories.genre import GenreRepository
from core.sa.repositories.series import SeriesRepository
from schemas import (
    UserSchema, UserCreate, BookSchema, BookStatusUpdate, BookUserSchema,
    BookWantedSchema, AuthorSchema, AuthorSubscriptionCreate, SeriesSubscriptionCreate,
    UserAuthorSubscriptionSchema, UserSeriesSubscriptionSchema, GenreSchema, PaginatedResponse,
    SeriesSchema, BasicBookSchema
)

app = FastAPI()

# CORS configuration
origins = [
    "http://192.168.86.221:5173",  # Your Vite dev server
    "http://localhost:5173",        # Local Vite dev server
    "http://192.168.86.221:4173",  # Your Vite dev server
    "http://localhost:4173",        # Local Vite dev server
    "http://192.168.86.221",       # Production URL
    "http://localhost",             # Local production URL
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    db = Database()  # Create an instance of your Database class
    db.init_db()  # Initialize the database schema
    db.close_session()

@app.get("/")
async def root():
    return {"message": "Hello World"}

# User Endpoints
@app.post("/users", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    try:
        repo = UserRepository(db)
        db_user = repo.create_user(user.name)
        return db_user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.get("/users", response_model=PaginatedResponse[UserSchema])
def get_users(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=10, le=100, description="Maximum number of users to return"),
    query: str = Query(default="", description="Search query to filter users by name")
):
    repo = UserRepository(db)
    
    # Get total number of users
    total_items = repo.count_users()

    # Calculate pagination metadata
    total_pages = (total_items + limit - 1) // limit

    # Calculate skip (offset) from page
    skip = (page - 1) * limit

    # Get paginated users
    users = repo.search_users(query=query, limit=limit, offset=skip)

    # Construct and return the PaginatedResponse
    return PaginatedResponse[UserSchema](
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        data=users,
    )

@app.get("/user/{user_id}", response_model=UserSchema)
def get_user(user_id: int, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    db_user = repo.get_by_id(user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return db_user

@app.put("/user/{user_id}", response_model=UserSchema)
def update_user(user_id: int, user: UserCreate, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    db_user = repo.update_user(user_id, user.name)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return db_user

# User Book Endpoints

@app.get("/user/{user_id}/book/{work_id}", response_model=BookSchema)
def get_book_with_user_status(
    user_id: int,
    work_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a single book with user-specific information (status and wanted state).
    Genres are ordered by position when available.
    Series include their order information.
    """
    repo = BookRepository(db)
    book = repo.get_by_work_id(work_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    # Determine user's status for this book
    book_user = next(
        (bu for bu in book.book_users if bu.user_id == user_id), None
    )
    user_status = book_user.status if book_user else None

    # Check if the book is in the user's wanted list
    wanted = any(bw.user_id == user_id for bw in book.book_wanted)

    # Sort genres by position if available
    sorted_genres = sorted(
        book.book_genres,
        key=lambda bg: (bg.position if bg.position is not None else float('inf'))
    )
    genres = [bg.genre for bg in sorted_genres]

    # Process series with their order information
    series_with_order = []
    for book_series in book.book_series:
        series_schema = SeriesSchema.model_validate(book_series.series)
        series_dict = series_schema.model_dump()
        series_dict['order'] = book_series.series_order
        series_with_order.append(series_dict)

    # Process authors with their roles
    authors_with_roles = []
    for book_author in book.book_authors:
        author_schema = AuthorSchema.model_validate(book_author.author)
        author_dict = author_schema.model_dump()
        author_dict['role'] = book_author.role
        authors_with_roles.append(author_dict)

    # Get similar books from both similar_to and similar_books relationships
    similar_books = []
    
    # Add books that this book is similar to
    for similar in book.similar_to:
        similar_book = similar.similar_book
        # Get user status for this similar book
        similar_book_user = next(
            (bu for bu in similar_book.book_users if bu.user_id == user_id), None
        )
        similar_book_status = similar_book_user.status if similar_book_user else None
        # Check if the similar book is wanted
        similar_book_wanted = any(bw.user_id == user_id for bw in similar_book.book_wanted)
        
        similar_books.append({
            "goodreads_id": similar_book.goodreads_id,
            "work_id": similar_book.work_id,
            "title": similar_book.title,
            "goodreads_rating": similar_book.goodreads_rating,
            "goodreads_votes": similar_book.goodreads_votes,
            "hidden": similar_book.hidden,
            "user_status": similar_book_status,
            "wanted": similar_book_wanted,
            "authors": [
                {
                    "goodreads_id": ba.author.goodreads_id,
                    "name": ba.author.name
                }
                for ba in similar_book.book_authors
                if ba.role == "Author"
            ]
        })
    
    # Add books that are similar to this book
    for similar in book.similar_books:
        similar_book = similar.book
        # Get user status for this similar book
        similar_book_user = next(
            (bu for bu in similar_book.book_users if bu.user_id == user_id), None
        )
        similar_book_status = similar_book_user.status if similar_book_user else None
        # Check if the similar book is wanted
        similar_book_wanted = any(bw.user_id == user_id for bw in similar_book.book_wanted)
        
        similar_books.append({
            "goodreads_id": similar_book.goodreads_id,
            "work_id": similar_book.work_id,
            "title": similar_book.title,
            "goodreads_rating": similar_book.goodreads_rating,
            "goodreads_votes": similar_book.goodreads_votes,
            "hidden": similar_book.hidden,
            "user_status": similar_book_status,
            "wanted": similar_book_wanted,
            "authors": [
                {
                    "goodreads_id": ba.author.goodreads_id,
                    "name": ba.author.name
                }
                for ba in similar_book.book_authors
                if ba.role == "Author"
            ]
        })

    # Create the base book dictionary
    book_dict = BasicBookSchema.model_validate(book).model_dump()
    
    # Update with user-specific information and relationships
    book_dict.update({
        "user_status": user_status,
        "wanted": wanted,
        "genres": genres,
        "series": series_with_order,
        "authors": authors_with_roles,
        "similar_books": similar_books
    })

    # Now validate the complete dictionary with BookSchema
    return BookSchema.model_validate(book_dict)

@app.get("/user/{user_id}/books", response_model=PaginatedResponse[BasicBookSchema])
def get_user_books(
    user_id: int,
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=10, le=100, description="Maximum number of books to return"),
):
    """
    Retrieves a paginated list of non-hidden books from the database with user's status,
    along with pagination metadata.
    """
    repo = BookRepository(db)
    # Get total number of books
    total_items = repo.count_books()

    # Calculate pagination metadata
    total_pages = (total_items + limit - 1) // limit  # Integer division for page count

    # Calculate skip (offset) from page and limit
    skip = (page - 1) * limit  # Calculate skip from page

    books = repo.search_books(limit=limit, offset=skip)

    result = []
    for book in books:
        if book.hidden:
            continue

        # Determine user's status for this book
        book_user = next(
            (bu for bu in book.book_users if bu.user_id == user_id), None
        )
        user_status = book_user.status if book_user else None

        # Check if the book is in the user's wanted list
        wanted = any(bw.user_id == user_id for bw in book.book_wanted)

        # Create the BookSchema with user-specific information
        book_schema = BasicBookSchema.model_validate(book).model_copy(
            update={  # Use update to override values
                "user_status": user_status,
                "wanted": wanted,
            },
        )
        result.append(book_schema)

    # Construct and return the PaginatedResponse
    return PaginatedResponse[BasicBookSchema](
        page=page,  # Pass through page param
        total_pages=total_pages,
        total_items=total_items,
        data=result,
    )

@app.put("/user/{user_id}/book/{work_id}", response_model=BookUserSchema)
def update_book_status(user_id: int, work_id: str, status_update: BookStatusUpdate, db: Session = Depends(get_db)):
    repo = BookRepository(db)
    user_repo = UserRepository(db)
    book_user = repo.update_book_status(
        user_id=user_id,
        work_id=work_id,
        status=status_update.status,
        source=status_update.source,
        started_at=status_update.started_at,
        finished_at=status_update.finished_at
    )
    if book_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book or User not found")
    return BookUserSchema.from_orm(book_user)

@app.delete("/user/{user_id}/book/{work_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book_status(user_id: int, work_id: str, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    if not repo.delete_book_status(user_id, work_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book status not found")
    return

@app.get("/user/{user_id}/books/recommended", response_model=PaginatedResponse[BasicBookSchema])
def get_recommended_books(
    user_id: int,
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=10, le=100, description="Maximum number of books to return"),
):
    """
    Get a paginated list of recommended books for the user.
    """
    repo = UserRepository(db)
    
    # Get total number of recommended books
    total_items = repo.count_similar_books_for_user_reads(user_id)

    # Calculate pagination metadata
    total_pages = (total_items + limit - 1) // limit

    # Calculate skip (offset) from page
    skip = (page - 1) * limit

    # Get paginated recommended books
    recommended_books = repo.get_recommended_books(
        user_id=user_id,
        limit=limit,
        offset=skip
    )

    # Extract just the books from the recommendations (ignore scores and breakdowns)
    books = [book for book, score, breakdown in recommended_books]

    # Construct and return the PaginatedResponse
    return PaginatedResponse[BasicBookSchema](
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        data=books,
    )

@app.get("/user/{user_id}/books/on-deck", response_model=PaginatedResponse[BasicBookSchema])
def get_on_deck_books(
    user_id: int,
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=10, le=100, description="Maximum number of books to return"),
):
    repo = UserRepository(db)
    
    # Get total number of on-deck books
    total_items = len(repo.get_on_deck_books(user_id))

    # Calculate pagination metadata
    total_pages = (total_items + limit - 1) // limit

    # Calculate skip (offset) from page
    skip = (page - 1) * limit

    # Get paginated on-deck books
    books = repo.get_on_deck_books(user_id, limit=limit, offset=skip)

    # Construct and return the PaginatedResponse
    return PaginatedResponse[BasicBookSchema](
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        data=books,
    )

@app.get("/user/{user_id}/books/wanted", response_model=List[BookWantedSchema])
def get_wanted_books(user_id: int, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    wanted_books = repo.get_wanted_books(user_id)
    return [BookWantedSchema.from_orm(book_wanted) for book_wanted, book in wanted_books]

@app.get("/user/{user_id}/books/complete", response_model=PaginatedResponse[BasicBookSchema])
def get_completed_books(
    user_id: int,
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=10, le=100, description="Maximum number of books to return"),
):
    """
    Get a paginated list of books that the user has completed, ordered by most recently finished.
    """
    repo = UserRepository(db)
    
    # Get total number of completed books
    total_items = repo.count_user_books_by_statuses(user_id, ["completed"])

    # Calculate pagination metadata
    total_pages = (total_items + limit - 1) // limit

    # Calculate skip (offset) from page
    skip = (page - 1) * limit

    # Get paginated completed books
    books = repo.get_user_books_by_statuses(
        user_id=user_id,
        statuses=["completed"],
        limit=limit,
        offset=skip
    )

    # Construct and return the PaginatedResponse
    return PaginatedResponse[BasicBookSchema](
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        data=books,
    )

@app.get("/user/{user_id}/books/recent", response_model=PaginatedResponse[BasicBookSchema])
def get_recent_books(
    user_id: int,
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=10, le=100, description="Maximum number of books to return"),
):
    """
    Get a paginated list of recently created books, ordered by creation date.
    Only includes non-hidden books with a valid source.
    """
    repo = UserRepository(db)
    
    # Get total number of books
    total_items = repo.count_recent_books()

    # Calculate pagination metadata
    total_pages = (total_items + limit - 1) // limit

    # Calculate skip (offset) from page
    skip = (page - 1) * limit

    # Get paginated books
    books = repo.get_recent_books(
        user_id=user_id,
        limit=limit,
        offset=skip
    )

    # Construct and return the PaginatedResponse
    return PaginatedResponse[BasicBookSchema](
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        data=books,
    )

# User Series Endpoints

@app.get("/user/{user_id}/series", response_model=List[UserSeriesSubscriptionSchema])
def get_user_series(user_id: int, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    series_subscriptions = repo.get_series_subscriptions(user_id)
    return [UserSeriesSubscriptionSchema.from_orm(subscription) for subscription, series in series_subscriptions]

@app.get("/user/{user_id}/series/{series_id}", response_model=PaginatedResponse[BasicBookSchema])
def get_series_books_with_user_status(
    user_id: int,
    series_id: str,
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=10, le=100, description="Maximum number of books to return"),
):
    repo = UserRepository(db)
    
    # Get total number of books in series
    all_books = repo.get_series_books_with_user_status(user_id, series_id)
    total_items = len(all_books)

    # Calculate pagination metadata
    total_pages = (total_items + limit - 1) // limit

    # Calculate skip (offset) from page
    skip = (page - 1) * limit

    # Get paginated books
    paginated_books = all_books[skip:skip + limit]

    # Process each book to include user status, wanted state, and series order
    processed_books = []
    for book in paginated_books:
        # Determine user's status for this book
        book_user = next(
            (bu for bu in book.book_users if bu.user_id == user_id), None
        )
        user_status = book_user.status if book_user else None

        # Check if the book is in the user's wanted list
        wanted = any(bw.user_id == user_id for bw in book.book_wanted)

        # Process series with their order information
        series_list = []
        for book_series in book.book_series:
            # Create a series model with the order included
            series = SeriesSchema.model_validate(book_series.series)
            series_dict = series.model_dump()
            series_dict['order'] = book_series.series_order
            series_list.append(SeriesSchema.model_validate(series_dict))

        # Create the BookSchema with user-specific information
        book_schema = BasicBookSchema.model_validate(book).model_copy(
            update={
                "user_status": user_status,
                "wanted": wanted,
                "series": series_list,
            },
        )
        processed_books.append(book_schema)

    # Construct and return the PaginatedResponse
    return PaginatedResponse[BasicBookSchema](
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        data=processed_books,
    )

# User Author Endpoints

@app.get("/user/{user_id}/authors", response_model=List[UserAuthorSubscriptionSchema])
def get_user_authors(user_id: int, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    author_subscriptions = repo.get_author_subscriptions(user_id)
    return [UserAuthorSubscriptionSchema.from_orm(subscription) for subscription, author in author_subscriptions]

@app.get("/user/{user_id}/author/{author_id}", response_model=AuthorSchema)
def get_author(user_id: int, author_id: str, db: Session = Depends(get_db)): #Added user_id, but not used
    repo = AuthorRepository(db)
    author = repo.get_by_goodreads_id(author_id)
    if author is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found")
    return author

@app.get("/user/{user_id}/author/{author_id}/books", response_model=List[BasicBookSchema])
def get_author_books(user_id: int, author_id: str, db: Session = Depends(get_db)): #Added user_id, but not used
    repo = BookRepository(db)
    books = repo.get_books_by_author(author_id)
    return books

# User Genre Endpoints (Example)
@app.get("/user/{user_id}/genres", response_model=List[GenreSchema])
def get_genres(user_id: int, db: Session = Depends(get_db)): #Added user_id, but not used
    repo = GenreRepository(db)
    return repo.search_genres(query="", limit=100)

@app.get("/user/{user_id}/genres/{genre_id}", response_model=GenreSchema) #Added user_id, but not used
def get_genre(genre_id: int, db: Session = Depends(get_db)):
    repo = GenreRepository(db)
    genre = repo.get_by_id(genre_id)
    if genre is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Genre not found")
    return genre

# User Subscription Endpoints

@app.post("/user/{user_id}/subscriptions/author/{author_goodreads_id}", response_model=UserAuthorSubscriptionSchema, status_code=status.HTTP_201_CREATED)
def subscribe_to_author(
    user_id: int,
    author_goodreads_id: str,
    db: Session = Depends(get_db)
):
    """
    Subscribe a user to an author using the author's Goodreads ID.
    """
    repo = UserRepository(db)
    try:
        author_subscription = repo.subscribe_to_author(user_id, author_goodreads_id)
        if author_subscription is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found")
        return author_subscription
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.post("/user/{user_id}/subscriptions/series/{series_goodreads_id}", response_model=UserSeriesSubscriptionSchema, status_code=status.HTTP_201_CREATED)
def subscribe_to_series(
    user_id: int,
    series_goodreads_id: str,
    db: Session = Depends(get_db)
):
    """
    Subscribe a user to a series using the series' Goodreads ID.
    """
    repo = UserRepository(db)
    try:
        series_subscription = repo.subscribe_to_series(user_id, series_goodreads_id)
        if series_subscription is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Series not found")
        return series_subscription
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.delete("/user/{user_id}/subscriptions/author/{author_id}", status_code=status.HTTP_204_NO_CONTENT)
def unsubscribe_from_author(user_id: int, author_id: str, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    if not repo.unsubscribe_from_author(user_id, author_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    return

@app.delete("/user/{user_id}/subscriptions/series/{series_id}", status_code=status.HTTP_204_NO_CONTENT)
def unsubscribe_from_series(user_id: int, series_id: str, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    if not repo.unsubscribe_from_series(user_id, series_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    return

@app.get("/user/{user_id}/subscriptions/author", response_model=PaginatedResponse[UserAuthorSubscriptionSchema])
def get_user_author_subscriptions(
    user_id: int,
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=10, le=100, description="Maximum number of subscriptions to return"),
):
    """
    Get a paginated list of user's author subscriptions.
    """
    repo = UserRepository(db)
    
    # Get paginated author subscriptions
    subscriptions = repo.get_author_subscriptions(
        user_id=user_id,
        limit=limit,
        offset=(page - 1) * limit
    )
    
    # Get total count for pagination
    total_items = len(repo.get_author_subscriptions(user_id))
    total_pages = (total_items + limit - 1) // limit
    
    # Extract just the subscription objects (ignore author data)
    subscription_data = [subscription for subscription, _ in subscriptions]
    
    return PaginatedResponse[UserAuthorSubscriptionSchema](
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        data=subscription_data,
    )

@app.get("/user/{user_id}/subscriptions/series", response_model=PaginatedResponse[UserSeriesSubscriptionSchema])
def get_user_series_subscriptions(
    user_id: int,
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=10, le=100, description="Maximum number of subscriptions to return"),
):
    """
    Get a paginated list of user's series subscriptions.
    Each subscription includes the series info and the first three book IDs in the series.
    """
    repo = UserRepository(db)
    
    # Get paginated series subscriptions
    subscriptions = repo.get_series_subscriptions(
        user_id=user_id,
        limit=limit,
        offset=(page - 1) * limit
    )
    
    # Get total count for pagination
    total_items = len(repo.get_series_subscriptions(user_id))
    total_pages = (total_items + limit - 1) // limit
    
    # Process subscriptions to include first three book IDs
    subscription_data = []
    for subscription, series in subscriptions:
        # Get first three books in the series
        series_books = repo.get_series_books(series.goodreads_id)[:3]
        book_ids = [book.work_id for book in series_books]
        
        # Create subscription data with series info and book IDs
        sub_dict = UserSeriesSubscriptionSchema.from_orm(subscription)
        sub_dict.first_three_book_ids = book_ids
        subscription_data.append(sub_dict)
    
    return PaginatedResponse[UserSeriesSubscriptionSchema](
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        data=subscription_data,
    )

# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload
        reload_dirs=["api", "core"]  # Watch both api and core directories for changes
    )