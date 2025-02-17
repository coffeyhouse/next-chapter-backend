"""Change series_order to text

Revision ID: change_series_order_to_text
Revises: remove_book_columns
Create Date: 2024-03-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'change_series_order_to_text'
down_revision: Union[str, None] = 'remove_book_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create a temporary table with the new schema
    op.execute("""
        CREATE TABLE book_series_new (
            work_id TEXT,
            series_id TEXT,
            series_order TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (work_id, series_id),
            FOREIGN KEY (work_id) REFERENCES book(work_id),
            FOREIGN KEY (series_id) REFERENCES series(goodreads_id)
        )
    """)
    
    # Copy data from old table to new table, converting series_order to text
    op.execute("""
        INSERT INTO book_series_new 
        SELECT work_id, series_id, 
               CASE 
                   WHEN series_order IS NULL THEN NULL 
                   ELSE CAST(series_order AS TEXT) 
               END,
               created_at, updated_at
        FROM book_series
    """)
    
    # Drop old table
    op.execute("DROP TABLE book_series")
    
    # Rename new table to original name
    op.execute("ALTER TABLE book_series_new RENAME TO book_series")


def downgrade() -> None:
    # Create a temporary table with the old schema
    op.execute("""
        CREATE TABLE book_series_old (
            work_id TEXT,
            series_id TEXT,
            series_order REAL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (work_id, series_id),
            FOREIGN KEY (work_id) REFERENCES book(work_id),
            FOREIGN KEY (series_id) REFERENCES series(goodreads_id)
        )
    """)
    
    # Copy data from current table to old table, attempting to convert text back to real
    op.execute("""
        INSERT INTO book_series_old 
        SELECT work_id, series_id,
               CASE 
                   WHEN series_order IS NULL THEN NULL
                   WHEN CAST(series_order AS REAL) IS NULL THEN NULL
                   ELSE CAST(series_order AS REAL)
               END,
               created_at, updated_at
        FROM book_series
    """)
    
    # Drop new table
    op.execute("DROP TABLE book_series")
    
    # Rename old table to original name
    op.execute("ALTER TABLE book_series_old RENAME TO book_series") 