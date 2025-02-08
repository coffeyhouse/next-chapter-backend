# core/sa/models/book.py
from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, Table, DateTime
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

# Association tables for many-to-many relationships
book_author = Table(
    'book_author',
    Base.metadata,
    Column('work_id', String, ForeignKey('book.work_id'), primary_key=True),
    Column('author_id', String, ForeignKey('author.goodreads_id'), primary_key=True),
    Column('role', String)
)

book_genre = Table(
    'book_genre',
    Base.metadata,
    Column('work_id', String, ForeignKey('book.work_id'), primary_key=True),
    Column('genre_id', Integer, ForeignKey('genre.id'), primary_key=True)
)

book_similar = Table(
    'book_similar',
    Base.metadata,
    Column('work_id', String, ForeignKey('book.work_id'), primary_key=True),
    Column('similar_work_id', String, ForeignKey('book.work_id'), primary_key=True)
)

class Book(Base, TimestampMixin):
    __tablename__ = 'book'

    goodreads_id = Column(String, primary_key=True)
    work_id = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    published_date = Column(DateTime)
    published_state = Column(String)
    language = Column(String)
    calibre_id = Column(Integer)
    pages = Column(Integer)
    isbn = Column(String)
    goodreads_rating = Column(Float)
    goodreads_votes = Column(Integer)
    description = Column(String)
    image_url = Column(String)
    source = Column(String)
    hidden = Column(Boolean, default=False)

    # Relationships
    authors = relationship('Author', secondary='book_author', back_populates='books')
    genres = relationship('Genre', secondary='book_genre', back_populates='books')
    series = relationship('Series', secondary='book_series', back_populates='books')
    
    # Self-referential relationship for similar books
    similar_to = relationship(
        'Book',
        secondary=book_similar,
        primaryjoin=work_id==book_similar.c.work_id,
        secondaryjoin=work_id==book_similar.c.similar_work_id,
        backref='similar_books'
    )