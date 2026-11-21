"""merge_heads

Revision ID: ecfb29c6815e
Revises: 8bc62f9f90c6, d42a91c8e510
Create Date: 2026-11-22 00:23:06.053565

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ecfb29c6815e'
down_revision: Union[str, Sequence[str], None] = ('8bc62f9f90c6', 'd42a91c8e510')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
