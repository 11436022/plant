"""add reference sources

Revision ID: c37f8e92a411
Revises: a11e7c4d9f20
Create Date: 2026-07-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c37f8e92a411"
down_revision: Union[str, Sequence[str], None] = "a11e7c4d9f20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table_name in ("disease", "pests"):
        op.add_column(table_name, sa.Column("source_name", sa.String(length=100), nullable=True))
        op.add_column(table_name, sa.Column("source_url", sa.String(length=2048), nullable=True))
        op.add_column(table_name, sa.Column("source_record_id", sa.String(length=128), nullable=True))


def downgrade() -> None:
    for table_name in ("pests", "disease"):
        op.drop_column(table_name, "source_record_id")
        op.drop_column(table_name, "source_url")
        op.drop_column(table_name, "source_name")
