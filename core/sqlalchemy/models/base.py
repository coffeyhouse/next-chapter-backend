# core/sqlalchemy/models/base.py
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
from sqlalchemy import DateTime

class Base(DeclarativeBase):
    """Base class for all models"""
    pass

class TimestampMixin:
    """Mixin to add created_at, updated_at and last_synced_at columns"""
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)