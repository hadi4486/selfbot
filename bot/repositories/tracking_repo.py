"""
Repository لایه‌ی تنظیمات کانال ردیابی پیام‌های حذف/ویرایش‌شده.
"""

from sqlalchemy import select, delete, update
from ..db.engine import session_scope
from ..db.models_ext import TrackingChannelSettings


async def _get_or_create(session) -> TrackingChannelSettings:
    obj = await session.get(TrackingChannelSettings, 1)
    if obj is None:
        obj = TrackingChannelSettings(id=1)
        session.add(obj)
        await session.flush()
    return obj


async def get_settings() -> TrackingChannelSettings:
    """دریافت تنظیمات کانال ردیابی."""
    async with session_scope() as session:
        return await _get_or_create(session)


async def save_settings(
    *,
    enabled: bool,
    channel_id: int | None = None,
    channel_username: str | None = None,
    track_deleted: bool = True,
    track_edited: bool = True,
    track_private: bool = True,
    track_groups: bool = True,
) -> None:
    """ذخیره تنظیمات کانال ردیابی."""
    async with session_scope() as session:
        obj = await _get_or_create(session)
        obj.enabled = enabled
        obj.channel_id = channel_id
        obj.channel_username = channel_username
        obj.track_deleted = track_deleted
        obj.track_edited = track_edited
        obj.track_private = track_private
        obj.track_groups = track_groups


async def delete_log_entry(log_id: int) -> bool:
    """حذف یک ورودی از لاگ."""
    async with session_scope() as session:
        from ..db.models_ext import DeletedMessageLog
        result = await session.execute(
            delete(DeletedMessageLog).where(DeletedMessageLog.id == log_id)
        )
        return result.rowcount > 0


async def clear_logs() -> int:
    """پاک کردن تمام لاگ‌ها."""
    async with session_scope() as session:
        from ..db.models_ext import DeletedMessageLog
        result = await session.execute(delete(DeletedMessageLog))
        return result.rowcount