"""update_user_role

Revision ID: fd3e7c310580
Revises: 66b13dcc0f3d
Create Date: 2026-04-14 00:07:15.489325

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# Alembic 版本識別資訊。
revision: str = "fd3e7c310580"
down_revision: Union[str, Sequence[str], None] = "66b13dcc0f3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """套用使用者欄位的後續調整。"""

    op.alter_column(
        "user",
        "role",
        existing_type=mysql.VARCHAR(length=50),
        type_=sa.String(length=20),
        nullable=False,
        existing_server_default=sa.text("'user'"),
    )
    op.alter_column(
        "user",
        "created_at",
        existing_type=mysql.TIMESTAMP(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    op.create_index(op.f("ix_user_user_id"), "user", ["user_id"], unique=False)


def downgrade() -> None:
    """回滾使用者欄位的後續調整。"""

    op.drop_index(op.f("ix_user_user_id"), table_name="user")
    op.alter_column(
        "user",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        type_=mysql.TIMESTAMP(),
        existing_nullable=True,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    op.alter_column(
        "user",
        "role",
        existing_type=sa.String(length=20),
        type_=mysql.VARCHAR(length=50),
        nullable=True,
        existing_server_default=sa.text("'user'"),
    )
