# core/exclusions.py
from typing import Optional, Tuple, NamedTuple
from core.models.book import HiddenReason
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
        "books set",
        "novel collection",
        "Collection Set",
        "Book Set",
        "free preview",
        "other stories",
        "Summary & Analysis",
        "Music from the Motion Picture",
        "Illustrated Movie Companion",        
        "Illustrated guide",
        "Review Summary",
        "collection: "
    ],     
    "max_pages": 1800,                     # Exclude books with more than 1800 pages
}

class ExclusionResult(NamedTuple):
    reason: str
    hidden_reason: HiddenReason

def get_exclusion_reason(book: dict) -> Optional[ExclusionResult]:
    # Check title patterns first
    if "title" in book and book["title"]:
        title_lower = book["title"].lower()
        
        # Check for basic patterns
        for pattern in EXCLUSION_RULES.get("title_patterns", []):
            if pattern.lower() in title_lower:
                return ExclusionResult(
                    reason=f"title contains disallowed pattern '{pattern}'",
                    hidden_reason=HiddenReason.TITLE_PATTERN_MATCH
                )
        
        # Check for various number patterns in titles
        number_patterns = [
            r'series.*\d+\s*-\s*\d+',      # "Series 1-3", "Series 1 - 3"
            r'#\d+\s*-\s*\d+',             # "#1-3", "#1 - 3"
            r'novellas?\s*\d+\s*-\s*\d+',  # "Novellas 1-10", "Novella 1 - 3"
            r'set.*\d+\s*-\s*\d+',         # "Set 1-3", "Set 1 - 3"
            r'books?\s*\d+',               # "Books 1", "Book 2"
            r'volume[s\s]+\d+\s*-\s*\d+',  # "Volumes 1-3", "Volume 1 - 3"
            r'series.*set of \d+',         # "The Shepherd King Series, Set of 2 Books"
            r'series \d+ books',           # "Once Upon a Broken Heart Series 3 Books"
            r'\d+ books collection set',    # "3 Books Collection Set"
            r'\d+ books hardcover collection',  # "3 Books Hardcover Collection"
            r'series.*collection set',      # "Series Collection Set"
            r'.*\d+\s*books.*collection',   # Any title with "X books" and "collection"
            r'.*series.*set of.*books',      # Any series with "set of X books"
            r'chapters?\s*\d+\s*-\s*\d+',    # "Chapters 1-5", "Chapter 1 - 5"
            r'(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+book\s+collection',  # "Four Book Collection", "3 Book Collection"
            r'books?\s+[IVXivx]+\s*-\s*[IVXivx]+',  # "Books I-III", "Book I - V"
            r'vol\.?\s*\d+\s*-\s*\d+',     # "Vol. 1-4", "Vols 1-4"
            r'vols?\.?\s*\d+\s*-\s*\d+',   # "Vol. 1-4", "Vols 1-4"
            r'collection\s+\d+\s*-\s*\d+',  # "Collection 1-4"
            r'thrillers\s+\d+\s*-\s*\d+',   # "Thrillers 4-6"
            r'\d+\s*-\s*book\s+collection', # "2-Book Collection"
            r'series\s+\d+\s*-\s*book',     # "Series 2-Book"
            r'(?:collection|series|thrillers|books)\s+\d+\s*-\s*\d+:' # "Collection 1-4:", "Series 1-4:", etc. with colon
        ]
        
        for pattern in number_patterns:
            if re.search(pattern, title_lower):
                return ExclusionResult(
                    reason=f"title contains number pattern indicating multiple books",
                    hidden_reason=HiddenReason.TITLE_NUMBER_PATTERN
                )

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
                    return ExclusionResult(
                        reason=f"page count ({pages}) exceeds maximum limit of {max_pages}",
                        hidden_reason=HiddenReason.EXCEEDS_PAGE_LENGTH
                    )
            except (ValueError, TypeError):
                pass

        # Check votes
        min_votes = EXCLUSION_RULES.get("min_votes")
        if min_votes is not None and "goodreads_votes" in book:
            try:
                votes = int(book["goodreads_votes"])
                if votes < min_votes:
                    return ExclusionResult(
                        reason=f"votes ({votes}) are below the minimum threshold of {min_votes}.",
                        hidden_reason=HiddenReason.LOW_VOTE_COUNT
                    )
            except (ValueError, TypeError):
                return ExclusionResult(
                    reason="votes could not be determined.",
                    hidden_reason=HiddenReason.LOW_VOTE_COUNT
                )

        # Check description
        if EXCLUSION_RULES.get("require_description", False):
            if not book.get("description"):
                return ExclusionResult(
                    reason="description is missing.",
                    hidden_reason=HiddenReason.NO_DESCRIPTION
                )

    # Check genres (always check genres regardless of upcoming status)
    if "genres" in book and book["genres"]:
        for genre in book["genres"]:
            if genre.get("name") in EXCLUSION_RULES.get("genres", []):
                return ExclusionResult(
                    reason=f"genre '{genre.get('name')}' is disallowed.",
                    hidden_reason=HiddenReason.EXCLUDED_GENRE
                )

    return None

def should_exclude_book(book: dict) -> bool:
    return get_exclusion_reason(book) is not None
