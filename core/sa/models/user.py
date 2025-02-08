# core/sa/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from .base import Base, TimestampMixin

class BookUser(Base, TimestampMixin):
    __tablename__ = 'book_user'

    work_id: Mapped[str] = mapped_column(ForeignKey('book.work_id'), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.id'), primary_key=True)
    status: Mapped[str] = mapped_column(String)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    user = relationship('User', back_populates='book_users')
    book = relationship('Book', back_populates='book_users')

class User(Base, TimestampMixin):
    __tablename__ = 'user'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    # Relationships
    book_users = relationship('BookUser', back_populates='user')
    books = relationship('Book', secondary='book_user', viewonly=True)