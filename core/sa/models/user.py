# core/sa/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table, DateTime
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

# Association table for user's book statuses
book_user = Table(
    'book_user',
    Base.metadata,
    Column('work_id', String, ForeignKey('book.work_id'), primary_key=True),
    Column('user_id', Integer, ForeignKey('user.id'), primary_key=True),
    Column('status', String),
    Column('source', String),
    Column('started_at', DateTime),
    Column('finished_at', DateTime)
)

class User(Base, TimestampMixin):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    # Relationships
    books = relationship('Book', secondary=book_user, backref='users')