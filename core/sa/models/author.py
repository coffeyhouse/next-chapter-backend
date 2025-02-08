# core/sa/models/author.py
from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class Author(Base, TimestampMixin):
    __tablename__ = 'author'

    goodreads_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    bio = Column(String)
    image_url = Column(String)

    # Relationships
    books = relationship('Book', secondary='book_author', back_populates='authors')