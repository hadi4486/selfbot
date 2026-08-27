"""افزودنِ جدولِ کانال‌های مقصدِ ردیابِ ویرایش/حذفِ پیام: message_tracker_channels

Revision ID: 0010_message_tracker
Revises: 0009_assistant_schedule
Create Date: 2026-08-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0010_message_tracker"
down_revision: Union[str, None] = "0009_assistant_schedule"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "message_tracker_channels",
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("added_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("chat_id"),
    )


def downgrade() -> None:
    op.drop_table("message_tracker_channels")
