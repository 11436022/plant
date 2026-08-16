"""Merge 3 divergent branches

Revision ID: 8bc62f9f90c6
Revises: c37f8e92a411, c503f6c775cd, dca0981cea69
Create Date: 2026-08-16 16:06:31.169431

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8bc62f9f90c6'
down_revision: Union[str, Sequence[str], None] = ('c37f8e92a411', 'c503f6c775cd', 'dca0981cea69')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
