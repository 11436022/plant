"""Merge feature and main migration branches

Revision ID: e3b759302308
Revises: 8766043b40ed, 6cddf6c41ab7
Create Date: 2026-06-03 15:34:03.575114

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3b759302308'
down_revision: Union[str, Sequence[str], None] = ('8766043b40ed', '6cddf6c41ab7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
