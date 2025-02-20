"""merge_book_scraping_and_position

Revision ID: 213f09ba8e34
Revises: 575e4809f992, 2024_03_19_add_book_scraping_columns
Create Date: 2025-02-20 09:37:29.213987

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '213f09ba8e34'
down_revision: Union[str, None] = ('575e4809f992', '2024_03_19_add_book_scraping_columns')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
