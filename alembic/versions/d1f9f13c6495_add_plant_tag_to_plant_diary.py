"""add_plant_tag_to_plant_diary

Revision ID: d1f9f13c6495
Revises: ecfb29c6815e
Create Date: 2026-11-22 00:23:16.091828

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1f9f13c6495'
down_revision: Union[str, Sequence[str], None] = 'ecfb29c6815e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add plant_tag column to plant_diary."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c["name"] for c in inspector.get_columns("plant_diary")]
    if "plant_tag" not in columns:
        op.add_column("plant_diary", sa.Column("plant_tag", sa.String(50), nullable=True))


def downgrade() -> None:
    """Downgrade schema: Remove plant_tag column from plant_diary."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c["name"] for c in inspector.get_columns("plant_diary")]
    if "plant_tag" in columns:
        op.drop_column("plant_diary", "plant_tag")
