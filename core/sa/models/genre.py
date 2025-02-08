# core/sa/models/genre.py
from sqlalchemy import Integer, String
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .base import Base, TimestampMixin

class Genre(Base, TimestampMixin):
    __tablename__ = 'genre'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    # Relationships
    book_genres = relationship('BookGenre', back_populates='genre')
    
    # Convenience relationship
    books = relationship('Book', secondary='book_genre', viewonly=True)