"""Add BookWanted table

Revision ID: aeb280782a0d
Revises: 
Create Date: 2025-02-11 14:25:16.662923

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from alembic.operations import ops


# revision identifiers, used by Alembic.
revision: str = 'aeb280782a0d'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create book_wanted table with all constraints
    op.create_table('book_wanted',
        sa.Column('work_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.ForeignKeyConstraint(['work_id'], ['book.work_id']),
        sa.PrimaryKeyConstraint('work_id', 'user_id'),
        sa.UniqueConstraint('work_id', 'user_id', name='uix_book_wanted_work_user')
    )
    
    # Use batch operations for book_user table modifications
    with op.batch_alter_table('book_user') as batch_op:
        batch_op.create_unique_constraint('uix_book_users_user_work', ['user_id', 'work_id'])


def downgrade() -> None:
    # Use batch operations for book_user table modifications
    with op.batch_alter_table('book_user') as batch_op:
        batch_op.drop_constraint('uix_book_users_user_work', type_='unique')
    
    # Drop book_wanted table
    op.drop_table('book_wanted')
