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
    UserAuthorSubscriptionSchema, UserSeriesSubscriptionSchema, GenreSchema, PaginatedResponse
)

app = FastAPI()

# CORS configuration
origins = [
    "http://192.168.86.221:5173",  # Your Vite dev server
    "http://localhost:5173",        # Local Vite dev server
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

@app.get("/users", response_model=List[UserSchema])
def get_users(db: Session = Depends(get_db)):
    repo = UserRepository(db)
    return repo.search_users(query="", limit=100) #Return all users, limit to 100

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

@app.get(
    "/user/{user_id}/books", response_model=PaginatedResponse[BookSchema]
)  # Use PaginatedResponse
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
        book_schema = BookSchema.model_validate(book).model_copy(
            update={  # Use update to override values
                "user_status": user_status,
                "wanted": wanted,
            },
        )
        result.append(book_schema)

    # Construct and return the PaginatedResponse
    return PaginatedResponse[BookSchema](
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

@app.get("/user/{user_id}/books/recommended", response_model=List[BookSchema])
def get_recommended_books(user_id: int, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    recommended_books = repo.get_recommended_books(user_id)
    return [book for book, score, breakdown in recommended_books]

@app.get("/user/{user_id}/books/on-deck", response_model=List[BookSchema])
def get_on_deck_books(user_id: int, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    on_deck_books = repo.get_on_deck_books(user_id)
    return on_deck_books

@app.get("/user/{user_id}/books/wanted", response_model=List[BookWantedSchema])
def get_wanted_books(user_id: int, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    wanted_books = repo.get_wanted_books(user_id)
    return [BookWantedSchema.from_orm(book_wanted) for book_wanted, book in wanted_books]

# User Series Endpoints

@app.get("/user/{user_id}/series", response_model=List[UserSeriesSubscriptionSchema])
def get_user_series(user_id: int, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    series_subscriptions = repo.get_series_subscriptions(user_id)
    return [UserSeriesSubscriptionSchema.from_orm(subscription) for subscription, series in series_subscriptions]

@app.get("/user/{user_id}/series/{series_id}", response_model=List[BookSchema])
def get_series_books_with_user_status(user_id: int, series_id: str, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    books = repo.get_series_books_with_user_status(user_id, series_id)
    return books

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

@app.get("/user/{user_id}/author/{author_id}/books", response_model=List[BookSchema])
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

@app.post("/user/{user_id}/subscriptions/author", response_model=UserAuthorSubscriptionSchema, status_code=status.HTTP_201_CREATED)
def subscribe_to_author(user_id: int, subscription: AuthorSubscriptionCreate, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    try:
        author_subscription = repo.subscribe_to_author(user_id, subscription.author_goodreads_id)
        if author_subscription is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found")
        return author_subscription
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.post("/user/{user_id}/subscriptions/series", response_model=UserSeriesSubscriptionSchema, status_code=status.HTTP_201_CREATED)
def subscribe_to_series(user_id: int, subscription: SeriesSubscriptionCreate, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    try:
        series_subscription = repo.subscribe_to_series(user_id, subscription.series_goodreads_id)
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

# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)