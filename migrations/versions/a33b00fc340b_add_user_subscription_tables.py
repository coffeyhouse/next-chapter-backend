"""Add user subscription tables

Revision ID: a33b00fc340b
Revises: aeb280782a0d
Create Date: 2024-02-11 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a33b00fc340b'
down_revision: Union[str, None] = 'aeb280782a0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_author_subscription table
    op.create_table('user_author_subscription',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('author_goodreads_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['author_goodreads_id'], ['author.goodreads_id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('user_id', 'author_goodreads_id'),
        sa.UniqueConstraint('user_id', 'author_goodreads_id', name='uix_user_author_subscription')
    )
    
    # Create user_series_subscription table
    op.create_table('user_series_subscription',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('series_goodreads_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['series_goodreads_id'], ['series.goodreads_id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('user_id', 'series_goodreads_id'),
        sa.UniqueConstraint('user_id', 'series_goodreads_id', name='uix_user_series_subscription')
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('user_series_subscription')
    op.drop_table('user_author_subscription')
