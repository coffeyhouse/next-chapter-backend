# core/sa/models/library.py
from sqlalchemy import Integer, String, ForeignKey, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .base import Base, TimestampMixin, LastSyncedMixin

class Library(Base, TimestampMixin, LastSyncedMixin):
    __tablename__ = 'library'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    calibre_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    goodreads_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    work_id: Mapped[str] = mapped_column(String(255), ForeignKey('book.work_id'), nullable=False)
    isbn: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Relationships
    book = relationship('Book', back_populates='library_entries')

    __table_args__ = (
        # Search indexes
        Index('idx_library_title', 'title'),
        Index('idx_library_isbn', 'isbn'),
        Index('idx_library_calibre_id', 'calibre_id'),
        Index('idx_library_work_id', 'work_id'),
        
        # Sync tracking indexes
        Index('idx_library_last_synced_at', 'last_synced_at'),
        
        {'schema': 'public'}
    )