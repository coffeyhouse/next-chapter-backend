"""add book scraping columns

Revision ID: 2024_03_19_add_book_scraping_columns
Revises: remove_book_columns
Create Date: 2024-03-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from alembic import context


# revision identifiers, used by Alembic.
revision: str = '2024_03_19_add_book_scraping_columns'
down_revision: Union[str, None] = 'remove_book_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add all columns first
    op.add_column('book', sa.Column('scraping_priority', sa.Integer(), nullable=True))
    op.add_column('book', sa.Column('next_scrape_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('book', sa.Column('hidden_reason', sa.String(), nullable=True))

    # Add check constraint in a separate batch operation
    with op.batch_alter_table('book') as batch_op:
        batch_op.create_check_constraint(
            'ck_book_scraping_priority_range',
            'scraping_priority >= 1 AND scraping_priority <= 5'
        )


def downgrade() -> None:
    # Remove constraint first
    with op.batch_alter_table('book') as batch_op:
        batch_op.drop_constraint('ck_book_scraping_priority_range', type_='check')
    
    # Remove columns
    op.drop_column('book', 'hidden_reason')
    op.drop_column('book', 'next_scrape_at')
    op.drop_column('book', 'scraping_priority') 