"""add_position_to_book_genre

Revision ID: 575e4809f992
Revises: change_series_order_to_text
Create Date: 2024-03-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '575e4809f992'
down_revision: Union[str, None] = 'change_series_order_to_text'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add position column to book_genre table
    with op.batch_alter_table('book_genre') as batch_op:
        batch_op.add_column(sa.Column('position', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Remove position column from book_genre table
    with op.batch_alter_table('book_genre') as batch_op:
        batch_op.drop_column('position')
