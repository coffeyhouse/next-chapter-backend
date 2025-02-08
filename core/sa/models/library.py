# core/sa/models/library.py
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .base import Base, TimestampMixin, LastSyncedMixin

class Library(Base, TimestampMixin, LastSyncedMixin):
    __tablename__ = 'library'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    calibre_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    goodreads_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    work_id: Mapped[str] = mapped_column(ForeignKey('book.work_id'), nullable=False)
    isbn: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    book = relationship('Book', back_populates='library_entries')