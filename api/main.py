from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import books

app = FastAPI(
    title="Goodreads Companion API",
    description="API for managing books, authors, and reading lists",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(books.router, prefix="/api/v1")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}