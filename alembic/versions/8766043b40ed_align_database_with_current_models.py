"""align database with current models

Revision ID: 8766043b40ed
Revises: 2f64de060dd9
Create Date: 2026-06-03 15:19:03.807018

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '8766043b40ed'
down_revision: Union[str, Sequence[str], None] = '2f64de060dd9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Keep the initial schema; it already has the token FK and ID index.

    The original generated operations referred to constraints that the initial
    migration never created. Existing installations are repaired by the later
    diagnosis-audit migration, without inventing email verification timestamps.
    """
    pass


def downgrade() -> None:
    """There are no schema changes to undo at this revision."""
    pass
