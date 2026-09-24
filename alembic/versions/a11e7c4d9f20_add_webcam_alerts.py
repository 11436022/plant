"""add webcam alerts

Revision ID: a11e7c4d9f20
Revises: 8766043b40ed
Create Date: 2026-07-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a11e7c4d9f20"
down_revision: Union[str, Sequence[str], None] = "8766043b40ed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "webcam_alert",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("crop_id", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("status_name", sa.String(length=100), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("consecutive_matches", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(length=2048), nullable=False),
        sa.Column("email_sent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["crop_id"], ["crop.crop_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.user_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_webcam_alert_id"), "webcam_alert", ["id"], unique=False)
    op.create_index(op.f("ix_webcam_alert_user_id"), "webcam_alert", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_webcam_alert_user_id"), table_name="webcam_alert")
    op.drop_index(op.f("ix_webcam_alert_id"), table_name="webcam_alert")
    op.drop_table("webcam_alert")
