"""Allow null for email_verified_at in user table

Revision ID: 0ea8fef2d664
Revises: e3b759302308
Create Date: 2026-06-04 22:57:10.825961

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0ea8fef2d664'
down_revision: Union[str, Sequence[str], None] = 'e3b759302308'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('user', 'email_verified_at',
               existing_type=sa.DATETIME(),
               nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('user', 'email_verified_at',
               existing_type=sa.DATETIME(),
               nullable=False)