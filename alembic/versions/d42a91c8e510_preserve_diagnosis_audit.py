"""Preserve diagnosis provenance and allow pending email verification.

Revision ID: d42a91c8e510
Revises: c37f8e92a411
"""
from alembic import op
import sqlalchemy as sa

revision = "d42a91c8e510"
down_revision = "c37f8e92a411"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user") as batch:
        batch.alter_column("email_verified_at", existing_type=sa.DateTime(), nullable=True)
    op.execute(sa.text("UPDATE user SET email_verified_at = NULL WHERE is_email_verified = false"))
    for table in ("plant_diary", "webcam_alert"):
        op.add_column(table, sa.Column("requires_review", sa.Boolean(), nullable=False, server_default=sa.true()))
        op.add_column(table, sa.Column("grounding_source", sa.String(64), nullable=False, server_default="legacy_unverified"))
        op.add_column(table, sa.Column("reference_source", sa.String(100), nullable=True))
        op.add_column(table, sa.Column("reference_url", sa.String(2048), nullable=True))
        op.add_column(table, sa.Column("reference_record_id", sa.String(128), nullable=True))
    op.add_column("plant_diary", sa.Column("category", sa.String(20), nullable=False, server_default="unknown"))
    op.add_column("webcam_alert", sa.Column("session_id", sa.String(64), nullable=False, server_default="legacy"))
    op.add_column("webcam_alert", sa.Column("region_id", sa.String(64), nullable=False, server_default="full-frame"))


def downgrade():
    op.drop_column("webcam_alert", "region_id")
    op.drop_column("webcam_alert", "session_id")
    op.drop_column("plant_diary", "category")
    for table in ("plant_diary", "webcam_alert"):
        for name in ("reference_record_id", "reference_url", "reference_source", "grounding_source", "requires_review"):
            op.drop_column(table, name)
    # Pending users must keep NULL verification dates even when rolling back.
