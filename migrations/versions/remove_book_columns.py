"""Remove language, isbn, and calibre_id columns from book table

Revision ID: remove_book_columns
Revises: a33b00fc340b
Create Date: 2024-02-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'remove_book_columns'
down_revision: Union[str, None] = 'a33b00fc340b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the columns from the book table
    with op.batch_alter_table('book') as batch_op:
        batch_op.drop_column('language')
        batch_op.drop_column('isbn')
        batch_op.drop_column('calibre_id')


def downgrade() -> None:
    # Add the columns back to the book table
    with op.batch_alter_table('book') as batch_op:
        batch_op.add_column(sa.Column('language', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('isbn', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('calibre_id', sa.Integer(), nullable=True)) 