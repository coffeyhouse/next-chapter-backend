# core/sa/models/author.py
from datetime import datetime, UTC
from sqlalchemy import Column, String, DateTime, Text, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .base import Base, TimestampMixin, LastSyncedMixin

class Author(Base, TimestampMixin, LastSyncedMixin):
    __tablename__ = 'author'

    goodreads_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relationships
    book_authors = relationship('BookAuthor', back_populates='author')
    
    # Convenience relationship
    books = relationship('Book', secondary='book_author', viewonly=True)
    user_subscriptions = relationship('UserAuthorSubscription', back_populates='author')

    __table_args__ = (
        # Search indexes
        Index('idx_author_name', 'name'),
        
        # Sync tracking indexes
        Index('idx_author_last_synced_at', 'last_synced_at'),
        
        {'schema': 'public'}
    )