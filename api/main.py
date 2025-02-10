from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import books, users

app = FastAPI(
    title="Calibre Companion API",
    description="API for managing books, authors, and libraries",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(books.router)
app.include_router(users.router)

@app.get("/")
async def root():
    """Root endpoint returning API information."""
    return {
        "name": "Calibre Companion API",
        "version": "1.0.0",
        "status": "running"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}