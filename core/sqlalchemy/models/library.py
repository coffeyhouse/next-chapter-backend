# core/sqlalchemy/models/library.py
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class Library(Base, TimestampMixin):
    __tablename__ = 'library'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    calibre_id = Column(Integer)
    goodreads_id = Column(String, unique=True)
    work_id = Column(String, ForeignKey('book.work_id'), nullable=False)
    isbn = Column(String)

    # Relationships
    book = relationship('Book', backref='library_entry')