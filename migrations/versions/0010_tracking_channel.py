"""Add tracking channel and deleted message log tables.

Revision ID: 0010
Revises: 0009_assistant_schedule
Create Date: 2026-08-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0010'
down_revision: Union[str, None] = '0009_assistant_schedule'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # جدول لاگ پیام‌های حذف/ویرایش‌شده
    op.create_table(
        'deleted_message_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('sender_id', sa.BigInteger(), nullable=True),
        sa.Column('sender_name', sa.Text(), nullable=True),
        sa.Column('sender_username', sa.String(length=64), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('event_type', sa.String(length=16), nullable=False),
        sa.Column('is_private', sa.Boolean(), nullable=False),
        sa.Column('chat_title', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_deleted_log_chat_id', 'deleted_message_log', ['chat_id'])
    op.create_index('ix_deleted_log_sender_id', 'deleted_message_log', ['sender_id'])
    op.create_index('ix_deleted_log_event_type', 'deleted_message_log', ['event_type'])
    op.create_index('ix_deleted_log_created_at', 'deleted_message_log', ['created_at'])

    # جدول تنظیمات کانال ردیابی
    op.create_table(
        'tracking_channel_settings',
        sa.Column('id', sa.SmallInteger(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('channel_id', sa.BigInteger(), nullable=True),
        sa.Column('channel_username', sa.String(length=64), nullable=True),
        sa.Column('track_deleted', sa.Boolean(), nullable=False),
        sa.Column('track_edited', sa.Boolean(), nullable=False),
        sa.Column('track_private', sa.Boolean(), nullable=False),
        sa.Column('track_groups', sa.Boolean(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('id = 1', name='ck_tracking_channel_singleton'),
    )


def downgrade() -> None:
    op.drop_table('tracking_channel_settings')
    op.drop_table('deleted_message_log')