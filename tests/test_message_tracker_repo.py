from .conftest import requires_db


@requires_db
async def test_channels_upsert_remove_clear():
    from bot.repositories import message_tracker_repo

    await message_tracker_repo.upsert_channel(100, "Log Channel A")
    await message_tracker_repo.upsert_channel(100, "Log Channel A renamed")  # آپدیت، نه رکورد تکراری
    channels = await message_tracker_repo.list_channels()
    assert channels == {"100": "Log Channel A renamed"}

    await message_tracker_repo.upsert_channel(200, "Log Channel B")
    await message_tracker_repo.remove_channel(100)
    assert await message_tracker_repo.list_channels() == {"200": "Log Channel B"}

    await message_tracker_repo.clear_channels()
    assert await message_tracker_repo.list_channels() == {}
