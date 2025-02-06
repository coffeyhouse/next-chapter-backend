# core/exclusions.py
from typing import Optional
import re

EXCLUSION_RULES = {
    "genres": ["Graphic Novel", "Comics", "Graphic Novels", "Graphic Novels Comics", "Manga", "Comic Book", "Anime", "Cookbooks", "Colouring", "Colouring Books", "Picture Books"],  # Example: exclude these genres
    "min_votes": 100,                       # Exclude books with fewer than 10 votes
    "require_description": True,            # Exclude books missing a description
    "title_patterns": [                     # Exclude titles containing these patterns (case insensitive)
        " / ", 
        "boxed", 
        "omnibus", 
        "sampler", 
        " bundle", 
        "novels", 
        "box set", 
        "complete collection", 
        "trilogy", 
        "anthology",
        "books set"
    ],     
    "max_pages": 1800,                     # Exclude books with more than 1800 pages
}

def get_exclusion_reason(book: dict) -> Optional[str]:
    # Check title patterns first
    if "title" in book and book["title"]:
        title_lower = book["title"].lower()
        
        # Check for basic patterns
        for pattern in EXCLUSION_RULES.get("title_patterns", []):
            if pattern.lower() in title_lower:
                return f"title contains disallowed pattern '{pattern}'"
        
        # Check for various number patterns in titles
        number_patterns = [
            r'series.*\d+\s*-\s*\d+',      # "Series 1-3", "Series 1 - 3"
            r'#\d+\s*-\s*\d+',             # "#1-3", "#1 - 3"
            r'novellas?\s*\d+\s*-\s*\d+',  # "Novellas 1-10", "Novella 1 - 3"
            r'set.*\d+\s*-\s*\d+',         # "Set 1-3", "Set 1 - 3"
            r'books?\s*\d+',               # "Books 1", "Book 2"
            r'volume[s\s]+\d+\s*-\s*\d+'   # "Volumes 1-3", "Volume 1 - 3"
        ]
        
        for pattern in number_patterns:
            if re.search(pattern, title_lower):
                return f"title contains number pattern indicating multiple books"

    # Check if book is upcoming
    is_upcoming = book.get("published_state") == "upcoming"

    # Skip the following checks for upcoming books
    if not is_upcoming:
        # Check page count
        max_pages = EXCLUSION_RULES.get("max_pages")
        if max_pages is not None and "pages" in book and book["pages"]:
            try:
                pages = int(book["pages"])
                if pages > max_pages:
                    return f"page count ({pages}) exceeds maximum limit of {max_pages}"
            except (ValueError, TypeError):
                pass

        # Check votes
        min_votes = EXCLUSION_RULES.get("min_votes")
        if min_votes is not None and "goodreads_votes" in book:
            try:
                votes = int(book["goodreads_votes"])
                if votes < min_votes:
                    return f"votes ({votes}) are below the minimum threshold of {min_votes}."
            except (ValueError, TypeError):
                return "votes could not be determined."

        # Check description
        if EXCLUSION_RULES.get("require_description", False):
            if not book.get("description"):
                return "description is missing."

    # Check genres (always check genres regardless of upcoming status)
    if "genres" in book and book["genres"]:
        for genre in book["genres"]:
            if genre.get("name") in EXCLUSION_RULES.get("genres", []):
                return f"genre '{genre.get('name')}' is disallowed."

    return None

def should_exclude_book(book: dict) -> bool:
    return get_exclusion_reason(book) is not None
