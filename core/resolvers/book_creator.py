from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from ..sa.repositories.book import BookRepository
from ..sa.models import Book, Author, Genre, Series, BookAuthor, BookGenre, BookSeries
from ..scrapers.book_scraper import BookScraper
from datetime import datetime, UTC

class BookCreator:
    def __init__(self, session: Session, scrape: bool = False):
        self.session = session
        self.book_repository = BookRepository(session)
        self.book_scraper = BookScraper(scrape)

    def create_book_from_goodreads(self, goodreads_id: str) -> Optional[Book]:
        """
        Scrapes a book from Goodreads and creates it in the database
        
        Args:
            goodreads_id: Goodreads ID of the book to scrape and create
            
        Returns:
            Created Book object or None if book already exists
        """
                
        # Check if book already exists by goodreads_id
        existing_book = self.book_repository.get_by_goodreads_id(goodreads_id)
        if existing_book:
            return None

        # Scrape book data
        book_data = self.book_scraper.scrape_book(goodreads_id)
        if not book_data:
            return None

        # Check if book exists by work_id
        work_id = book_data.get('work_id')
        if work_id:
            existing_book = self.book_repository.get_by_work_id(work_id)
            if existing_book:
                return None

        # Create the book
        return self.create_book(book_data)

    def create_book(self, book_data: Dict[str, Any]) -> Book:
        """
        Creates a book and its relationships from provided data
        
        Args:
            book_data: Dictionary containing book data
            
        Returns:
            Created Book object
        
        Raises:
            ValueError: If a book with the same work_id already exists
        """
        # Check if book exists by work_id
        work_id = book_data.get('work_id')
        if work_id:
            existing_book = self.book_repository.get_by_work_id(work_id)
            if existing_book:
                raise ValueError(f"Book with work_id {work_id} already exists")

        # Create the main book entity
        book = self._create_book_entity(book_data)
        self.session.add(book)
        
        # Create relationships
        self._create_author_relationships(book, book_data.get('authors', []))
        self._create_genre_relationships(book, book_data.get('genres', []))
        self._create_series_relationships(book, book_data.get('series', []))
        
        self.session.commit()
        return book

    def _create_book_entity(self, book_data: Dict[str, Any]) -> Book:
        """Creates the main book entity without relationships"""        
        now = datetime.now(UTC)
        
        return Book(
            goodreads_id=book_data['goodreads_id'],
            title=book_data['title'],
            work_id=book_data['work_id'],
            published_date=self._parse_date(book_data.get('published_date')),
            published_state=book_data.get('published_state'),
            language=book_data.get('language'),
            pages=book_data.get('pages'),
            isbn=book_data.get('isbn'),
            goodreads_rating=book_data.get('goodreads_rating'),
            goodreads_votes=book_data.get('goodreads_votes'),
            description=book_data.get('description'),
            image_url=book_data.get('image_url'),
            source=book_data.get('source', 'goodreads'),
            hidden=book_data.get('hidden', False),
            last_synced_at=now
        )

    def _create_or_get_author(self, author_data: Dict[str, Any]) -> Tuple[Author, bool]:
        """Creates or retrieves an author. Returns (author, was_created)"""
        author = self.session.query(Author).filter_by(
            goodreads_id=author_data['goodreads_id']
        ).first()
        
        created = False
        if not author:
            author = Author(
                goodreads_id=author_data['goodreads_id'],
                name=author_data['name']
            )
            self.session.add(author)
            created = True
            
        return author, created

    def _create_or_get_genre(self, genre_data: Dict[str, Any]) -> Tuple[Genre, bool]:
        """Creates or retrieves a genre. Returns (genre, was_created)"""
        genre = self.session.query(Genre).filter_by(
            name=genre_data['name']
        ).first()
        
        created = False
        if not genre:
            genre = Genre(name=genre_data['name'])
            self.session.add(genre)
            self.session.flush()  # Need to flush to get the genre.id
            created = True
            
        return genre, created

    def _create_or_get_series(self, series_data: Dict[str, Any]) -> Tuple[Series, bool]:
        """Creates or retrieves a series. Returns (series, was_created)"""
        series = self.session.query(Series).filter_by(
            goodreads_id=series_data['goodreads_id']
        ).first()
        
        created = False
        if not series:
            series = Series(
                goodreads_id=series_data['goodreads_id'],
                title=series_data.get('name', series_data.get('title'))
            )
            self.session.add(series)
            created = True
            
        return series, created

    def _create_author_relationships(self, book: Book, authors_data: List[Dict[str, Any]]) -> None:
        """Creates author relationships for a book"""
        for author_data in authors_data:
            author, _ = self._create_or_get_author(author_data)
            book_author = BookAuthor(
                work_id=book.work_id,
                author_id=author.goodreads_id,
                role=author_data.get('role')
            )
            self.session.add(book_author)

    def _create_genre_relationships(self, book: Book, genres_data: List[Dict[str, Any]]) -> None:
        """Creates genre relationships for a book"""
        for genre_data in genres_data:
            genre, _ = self._create_or_get_genre(genre_data)
            book_genre = BookGenre(
                work_id=book.work_id,
                genre_id=genre.id
            )
            self.session.add(book_genre)

    def _create_series_relationships(self, book: Book, series_data: List[Dict[str, Any]]) -> None:
        """Creates series relationships for a book"""
        for series_item in series_data:
            series, _ = self._create_or_get_series(series_item)
            book_series = BookSeries(
                work_id=book.work_id,
                series_id=series.goodreads_id,
                series_order=series_item.get('order')
            )
            self.session.add(book_series)

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse a date string from various formats"""
        if not date_str:
            return None
            
        formats = [
            '%Y-%m-%dT%H:%M:%S.%f',  # 2021-05-04T00:00:00.000000
            '%Y-%m-%d',              # 2021-05-04
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None 