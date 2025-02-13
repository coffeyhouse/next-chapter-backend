from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import books, users

app = FastAPI(
    title="Calibre Companion API",
    description="API for managing books, authors, and libraries",
    version="1.0.0"
)

# Configure CORS
origins = [
    "http://192.168.86.221:5173",  # Your Vite dev server
    "http://localhost:5173",        # Local Vite dev server
    "http://192.168.86.221",       # Production URL
    "http://localhost",             # Local production URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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