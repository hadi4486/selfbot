"""
ذخیره‌سازی گزارش فعالیت روزانه - از طریق Repository Layer.
"""

from ..repositories import activity_repo
from typing import List, Optional


async def increment_messages(chat_id: int, count: int = 1) -> None:
    return await activity_repo.increment_messages(chat_id, count)


async def increment_warnings(chat_id: int, count: int = 1) -> None:
    return await activity_repo.increment_warnings(chat_id, count)


async def increment_deleted(chat_id: int, count: int = 1) -> None:
    return await activity_repo.increment_deleted(chat_id, count)


async def increment_joined(chat_id: int, count: int = 1) -> None:
    return await activity_repo.increment_joined(chat_id, count)


async def increment_left(chat_id: int, count: int = 1) -> None:
    return await activity_repo.increment_left(chat_id, count)


async def get_summary(chat_id: int, days: int = 7) -> dict:
    return await activity_repo.get_summary(chat_id, days)