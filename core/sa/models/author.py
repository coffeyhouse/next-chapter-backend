# core/sa/models/author.py
from sqlalchemy import String
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .base import Base, TimestampMixin, LastSyncedMixin

class Author(Base, TimestampMixin, LastSyncedMixin):
    __tablename__ = 'author'

    goodreads_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    bio: Mapped[str | None] = mapped_column(String, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    book_authors = relationship('BookAuthor', back_populates='author')
    
    # Convenience relationship
    books = relationship('Book', secondary='book_author', viewonly=True)