"""add email verification and reset tokens

Revision ID: e6b21b1a4c1f
Revises: d69bf324a789
Create Date: 2026-04-29 00:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e6b21b1a4c1f"
down_revision: Union[str, Sequence[str], None] = "d69bf324a789"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 為 user 表加入信箱驗證狀態，舊帳號預設視為已驗證，避免直接鎖住既有使用者。
    op.add_column(
        "user",
        sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    )
    op.add_column("user", sa.Column("email_verified_at", sa.DateTime(), nullable=True))

    # 一次性 token 表同時服務驗證信與忘記密碼流程。
    op.create_table(
        "user_one_time_tokens",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("token_hash", name="uq_user_one_time_tokens_token_hash"),
    )
    op.create_index(
        "ix_user_one_time_tokens_user_purpose",
        "user_one_time_tokens",
        ["user_id", "purpose"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_user_one_time_tokens_user_purpose", table_name="user_one_time_tokens")
    op.drop_table("user_one_time_tokens")
    op.drop_column("user", "email_verified_at")
    op.drop_column("user", "is_email_verified")
