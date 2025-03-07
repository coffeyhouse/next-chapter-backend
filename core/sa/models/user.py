# core/sa/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime, UTC
from .base import Base, TimestampMixin
from sqlalchemy.types import TypeDecorator

class SafeDateTime(TypeDecorator):
    """Custom DateTime type that handles empty strings as None"""
    impl = DateTime(timezone=True)  # Ensure timezone support
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value == '':
            return None
        return value

    def process_result_value(self, value, dialect):
        if value == '':
            return None
        return value

class BookUser(Base, TimestampMixin):
    __tablename__ = 'book_user'

    work_id: Mapped[str] = mapped_column(String(255), ForeignKey('book.work_id'), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.id'), primary_key=True)
    status: Mapped[str] = mapped_column(String(50))
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(SafeDateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(SafeDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(SafeDateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(SafeDateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relationships
    user = relationship('User', back_populates='book_users')
    book = relationship('Book', back_populates='book_users')

    __table_args__ = (
        UniqueConstraint('user_id', 'work_id', name='uix_book_users_user_work'),
    )

class User(Base, TimestampMixin):
    __tablename__ = 'user'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(SafeDateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(SafeDateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relationships
    book_users = relationship('BookUser', back_populates='user')
    books = relationship('Book', secondary='book_user', viewonly=True)
    book_wanted = relationship('BookWanted', back_populates='user')
    author_subscriptions = relationship('UserAuthorSubscription', back_populates='user')
    series_subscriptions = relationship('UserSeriesSubscription', back_populates='user')

class BookWanted(Base):
    """Books that users want to acquire."""
    __tablename__ = "book_wanted"
    
    work_id = Column(String(255), ForeignKey("book.work_id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), primary_key=True)
    source = Column(String(50))  # Where they want to get it from
    created_at = Column(SafeDateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(SafeDateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    
    # Relationships
    user = relationship("User", back_populates="book_wanted")
    book = relationship("Book", back_populates="book_wanted")
    
    __table_args__ = (
        UniqueConstraint('work_id', 'user_id', name='uix_book_wanted_work_user'),
    )

class UserAuthorSubscription(Base):
    """Tracks which authors a user is subscribed to for updates."""
    __tablename__ = "user_author_subscription"
    
    user_id = Column(Integer, ForeignKey("user.id"), primary_key=True)
    author_goodreads_id = Column(String(255), ForeignKey("author.goodreads_id"), primary_key=True)
    created_at = Column(SafeDateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(SafeDateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    deleted_at = Column(SafeDateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="author_subscriptions")
    author = relationship("Author", back_populates="user_subscriptions")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'author_goodreads_id', name='uix_user_author_subscription'),
    )

class UserSeriesSubscription(Base):
    """Tracks which series a user is subscribed to for updates."""
    __tablename__ = "user_series_subscription"
    
    user_id = Column(Integer, ForeignKey("user.id"), primary_key=True)
    series_goodreads_id = Column(String(255), ForeignKey("series.goodreads_id"), primary_key=True)
    created_at = Column(SafeDateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(SafeDateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    deleted_at = Column(SafeDateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="series_subscriptions")
    series = relationship("Series", back_populates="user_subscriptions")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'series_goodreads_id', name='uix_user_series_subscription'),
    )