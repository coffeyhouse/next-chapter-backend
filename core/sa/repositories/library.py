from typing import List, Optional
from sqlalchemy import func, desc
from sqlalchemy.orm import Session, joinedload
from core.sa.models import Library, Book

class LibraryRepository:
    """Repository for managing Library entities."""

    def __init__(self, session: Session):
        """Initialize the repository with a database session.
        
        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

    def get_by_id(self, library_id: int) -> Optional[Library]:
        """Get a library entry by its ID.
        
        Args:
            library_id: The ID of the library entry to retrieve
            
        Returns:
            The Library object if found, None otherwise
        """
        return self.session.query(Library).filter(Library.id == library_id).first()

    def get_by_calibre_id(self, calibre_id: int) -> Optional[Library]:
        """Get a library entry by its Calibre ID.
        
        Args:
            calibre_id: The Calibre ID to search for
            
        Returns:
            The Library object if found, None otherwise
        """
        return self.session.query(Library).filter(Library.calibre_id == calibre_id).first()

    def get_by_goodreads_id(self, goodreads_id: str) -> Optional[Library]:
        """Get a library entry by its Goodreads ID.
        
        Args:
            goodreads_id: The Goodreads ID to search for
            
        Returns:
            The Library object if found, None otherwise
        """
        return self.session.query(Library).filter(Library.goodreads_id == goodreads_id).first()

    def get_by_isbn(self, isbn: str) -> List[Library]:
        """Get library entries by ISBN.
        
        Args:
            isbn: The ISBN to search for
            
        Returns:
            List of Library objects with matching ISBN
        """
        return self.session.query(Library).filter(Library.isbn == isbn).all()

    def search_by_title(self, query: str, limit: int = 20) -> List[Library]:
        """Search for library entries by title.
        
        Args:
            query: The search query string
            limit: Maximum number of results to return (default: 20)
            
        Returns:
            List of matching Library objects
        """
        return (
            self.session.query(Library)
            .filter(Library.title.ilike(f"%{query}%"))
            .limit(limit)
            .all()
        )

    def get_library_with_book(self, library_id: int) -> Optional[Library]:
        """Get a library entry with its associated book relationship.
        
        Args:
            library_id: The ID of the library entry
            
        Returns:
            The Library object with loaded book relationship if found, None otherwise
        """
        return (
            self.session.query(Library)
            .options(joinedload(Library.book))
            .filter(Library.id == library_id)
            .first()
        )

    def get_all_by_work_id(self, work_id: str) -> List[Library]:
        """Get all library entries for a specific work ID.
        
        Args:
            work_id: The work ID to search for
            
        Returns:
            List of Library objects with matching work ID
        """
        return self.session.query(Library).filter(Library.work_id == work_id).all()

    def create_entry(
        self,
        title: str,
        work_id: str,
        calibre_id: Optional[int] = None,
        goodreads_id: Optional[str] = None,
        isbn: Optional[str] = None
    ) -> Library:
        """Create a new library entry.
        
        Args:
            title: The title of the book
            work_id: The work ID of the book
            calibre_id: Optional Calibre ID
            goodreads_id: Optional Goodreads ID
            isbn: Optional ISBN
            
        Returns:
            The created Library object
        """
        library = Library(
            title=title,
            work_id=work_id,
            calibre_id=calibre_id,
            goodreads_id=goodreads_id,
            isbn=isbn
        )
        self.session.add(library)
        self.session.commit()
        return library

    def update_entry(
        self,
        library_id: int,
        title: Optional[str] = None,
        calibre_id: Optional[int] = None,
        goodreads_id: Optional[str] = None,
        isbn: Optional[str] = None
    ) -> Optional[Library]:
        """Update an existing library entry.
        
        Args:
            library_id: The ID of the library entry to update
            title: Optional new title
            calibre_id: Optional new Calibre ID
            goodreads_id: Optional new Goodreads ID
            isbn: Optional new ISBN
            
        Returns:
            The updated Library object if found, None otherwise
        """
        library = self.get_by_id(library_id)
        if not library:
            return None

        if title is not None:
            library.title = title
        if calibre_id is not None:
            library.calibre_id = calibre_id
        if goodreads_id is not None:
            library.goodreads_id = goodreads_id
        if isbn is not None:
            library.isbn = isbn

        self.session.commit()
        return library

    def delete_entry(self, library_id: int) -> bool:
        """Delete a library entry.
        
        Args:
            library_id: The ID of the library entry to delete
            
        Returns:
            True if the entry was deleted, False if not found
        """
        library = self.get_by_id(library_id)
        if not library:
            return False

        self.session.delete(library)
        self.session.commit()
        return True 