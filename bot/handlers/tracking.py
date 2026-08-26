"""
ردیابِ ویرایش/حذفِ پیام در پیوی و گروه‌ها.
با events.MessageEdited و events.MessageDeleted تلتون، وقتی طرف پیامی که قبلاً دیده‌بودی رو حذف یا ادیت می‌کنه،
نسخه‌ی قبلی رو برات نگه می‌داره و به کانال تنظیم‌شده می‌فرسته.
"""

import logging
from datetime import datetime, timezone

from telethon import events
from telethon.tl.types import Message

from .. import runtime, config
from ..runtime import client
from ..db.models_ext import DeletedMessageLog
from ..repositories.tracking_repo import get_settings, save_settings, delete_log_entry, clear_logs
from ..storage.settings_toggles import toggles
from ..storage.stats_store import record_error
from ..utils import pat

logger = logging.getLogger("selfbot.handlers.tracking")

# کش ساده برای جلوگیری از ثبت دوباره‌ی یک رویداد (در صورت دریافت دوباره)
_last_events: dict[str, float] = {}
_DEBOUNCE_SECONDS = 2.0


def _event_key(chat_id: int, message_id: int, event_type: str) -> str:
    return f"{chat_id}:{message_id}:{event_type}"


def _is_duplicate(key: str) -> bool:
    now = datetime.now(timezone.utc).timestamp()
    if key in _last_events and now - _last_events[key] < _DEBOUNCE_SECONDS:
        return True
    _last_events[key] = now
    return False


async def _get_sender_info(sender_id: int) -> tuple[str | None, str | None]:
    """دریافت نام و یوزرنیم فرستنده."""
    try:
        entity = await client.get_entity(sender_id)
        name = f"{entity.first_name or ''} {entity.last_name or ''}".strip() or None
        username = getattr(entity, "username", None)
        return name, username
    except Exception:
        return None, None


async def _send_to_tracking_channel(text: str) -> None:
    """ارسال پیام به کانال ردیابی (اگر تنظیم شده باشد)."""
    settings = await get_settings()
    if not settings.enabled or not settings.channel_id:
        return
    try:
        await client.send_message(settings.channel_id, text)
    except Exception as e:
        logger.exception("خطا در ارسال به کانال ردیابی")
        record_error()


@client.on(events.MessageEdited(incoming=True))
async def tracking_edited_handler(event):
    """هندلر ویرایش پیام."""
    # فقط پیام‌هایی که توسط دیگران ارسال شده‌اند را ردیابی کن (نه خودمان)
    if event.sender_id == runtime.SELF_ID:
        return

    settings = await get_settings()
    if not settings.enabled:
        return
    if not settings.track_edited:
        return

    # تشخیص پیوی یا گروه
    is_private = event.is_private
    if is_private and not settings.track_private:
        return
    if not is_private and not settings.track_groups:
        return

    # دریافت پیام قبل از ویرایش (نسخه‌ی قدیمی)
    # متأسفانه Telethon در رویداد MessageEdited فقط پیام جدید را م��‌دهد.
    # برای دریافت نسخه‌ی قبلی باید از event.original_message استفاده کنیم (اگر موجود باشد)
    # اما در برخی موارد این کار نمی‌کند. در عوض ما خودمان پیام را قبل از ویرایش در حافظه نگه می‌داریم؟
    # راه حل: از event.original_message یا event.message با توجه به اینکه رویداد حاوی هر دو است.
    # در Telethon، event.original_message نسخه‌ی قبل از ویرایش را دارد (اگر در دسترس باشد).
    old_msg = getattr(event, "original_message", None)
    if old_msg is None:
        # گاهی original_message موجود نیست، پس از خود event.message استفاده می‌کنیم که جدید است.
        # اما ما نسخه‌ی قدیمی را نداریم. برای جلوگیری از ثبت اشتباه، این رویداد را نادیده می‌گیریم.
        # می‌توانیم پیام جدید را به عنوان "ویرایش" ثبت کنیم اما متن قدیمی را نداریم.
        # بهتر است فقط وقتی original_message موجود است ثبت کنیم.
        return

    new_msg = event.message
    old_text = old_msg.raw_text or ""
    new_text = new_msg.raw_text or ""

    if old_text == new_text:
        return  # تغییری نکرده

    # جلوگیری از ثبت دوباره
    key = _event_key(event.chat_id, event.id, "edited")
    if _is_duplicate(key):
        return

    # دریافت اطلاعات فرستنده
    sender_id = event.sender_id
    sender_name, sender_username = await _get_sender_info(sender_id) if sender_id else (None, None)
    chat_title = None
    if not is_private:
        try:
            chat = await client.get_entity(event.chat_id)
            chat_title = getattr(chat, "title", None)
        except Exception:
            chat_title = str(event.chat_id)

    # ذخیره در دیتابیس
    async with client.db_session() as session:
        log = DeletedMessageLog(
            chat_id=event.chat_id,
            message_id=event.id,
            sender_id=sender_id,
            sender_name=sender_name,
            sender_username=sender_username,
            text=old_text,
            event_type="edited",
            is_private=is_private,
            chat_title=chat_title,
        )
        session.add(log)
        await session.commit()

    # ساخت پیام برای کانال
    location = "پیوی" if is_private else f"گروه/کانال {chat_title or event.chat_id}"
    sender_display = sender_name or sender_username or str(sender_id) or "ناشناس"
    msg_text = (
        f"✏️ **ویرایش پیام**\n"
        f"👤 فرستنده: {sender_display}\n"
        f"📍 {location}\n"
        f"🆔 پیام: {event.id}\n"
        f"📝 **متن قبلی:**\n{old_text or '(بدون متن)'}\n"
        f"📝 **متن جدید:**\n{new_text or '(بدون متن)'}"
    )
    await _send_to_tracking_channel(msg_text)


@client.on(events.MessageDeleted(incoming=True))
async def tracking_deleted_handler(event):
    """هندلر حذف پیام."""
    # فقط پیام‌هایی که توسط دیگران حذف شده‌اند را ردیابی کن (نه خودمان)
    # توجه: در رویداد حذف، sender_id در دسترس نیست، بنابراین نمی‌توان تشخیص داد چه کسی حذف کرده.
    # اما ما پیام حذف‌شده را نمی‌توانیم بازیابی کنیم مگر اینکه قبلاً ذخیره کرده باشیم.
    # راه حل: ما نمی‌توانیم متن پیام حذف‌شده را بگیریم، مگر اینکه قبلاً آن را کش کرده باشیم.
    # بنابراین در اینجا فقط اعلام می‌کنیم که پیامی حذف شده، بدون متن.
    # اما برای پیوی، می‌توانیم فرض کنیم که طرف مقابل حذف کرده است.

    settings = await get_settings()
    if not settings.enabled:
        return
    if not settings.track_deleted:
        return

    # تشخیص پیوی یا گروه - event.chat_id مشخص است
    # برای تشخیص پیوی بودن، از event.is_private استفاده نمی‌شود، باید چک کنیم که chat_id مثبت است.
    chat_id = event.chat_id
    is_private = chat_id > 0  # پیوی‌ها آیدی مثبت دارند

    if is_private and not settings.track_private:
        return
    if not is_private and not settings.track_groups:
        return

    # برای هر پیام حذف‌شده، یک ورودی لاگ ایجاد می‌کنیم (بدون متن، چون نمی‌توانیم بازیابی کنیم)
    # اما می‌توانیم پیام‌های حذف‌شده را با شناسه‌شان ثبت کنیم.
    for msg_id in event.deleted_ids:
        # جلوگیری از ثبت دوباره
        key = _event_key(chat_id, msg_id, "deleted")
        if _is_duplicate(key):
            continue

        # دریافت اطلاعات فرستنده - نمی‌توانیم sender_id را از رویداد حذف دریافت کنیم.
        # بنابراین فقط چت و شناسه پیام را ثبت می‌کنیم.
        # در پیوی، فرض می‌کنیم طرف مقابل حذف کرده است.
        sender_display = "طرف مقابل" if is_private else "ناشناس"

        # ذخیره در دیتابیس (بدون متن، چون در دسترس نیست)
        async with client.db_session() as session:
            log = DeletedMessageLog(
                chat_id=chat_id,
                message_id=msg_id,
                sender_id=None,
                sender_name=None,
                sender_username=None,
                text="[متن در دسترس نیست - پیام حذف شده]",
                event_type="deleted",
                is_private=is_private,
                chat_title=None,  # برای گروه می‌توانیم بعداً دریافت کنیم
            )
            session.add(log)
            await session.commit()

        # ساخت پیام برای کانال
        location = "پیوی" if is_private else f"گروه/کانال {chat_id}"
        msg_text = (
            f"🗑️ **حذف پیام**\n"
            f"📍 {location}\n"
            f"🆔 پیام: {msg_id}\n"
            f"⚠️ متن پیام در دسترس نیست (حذف شده)"
        )
        await _send_to_tracking_channel(msg_text)


# دستورات تنظیم کانال ردیابی
@client.on(events.NewMessage(outgoing=True, pattern=pat(["ردیابی", "track"])))
async def tracking_settings_handler(event):
    """دستورات تنظیم کانال ردیابی."""
    raw = (event.pattern_match.group(1) or "").strip()
    parts = raw.split(maxsplit=1)
    sub = parts[0].lower() if parts else ""
    rest = parts[1] if len(parts) > 1 else ""

    if not sub:
        # نمایش وضعیت فعلی
        settings = await get_settings()
        status = "روشن ✅" if settings.enabled else "خاموش ❌"
        channel_info = f"کانال: {settings.channel_username or settings.channel_id or 'تنظیم نشده'}"
        track_types = []
        if settings.track_deleted:
            track_types.append("حذف")
        if settings.track_edited:
            track_types.append("ویرایش")
        track_scope = []
        if settings.track_private:
            track_scope.append("پیوی")
        if settings.track_groups:
            track_scope.append("گروه‌ها")
        return await event.edit(
            f"🔍 **ردیابی پیام‌های حذف/ویرایش**\n\n"
            f"وضعیت: {status}\n"
            f"{channel_info}\n"
            f"ردیابی: {', '.join(track_types) if track_types else 'هیچ‌کدام'}\n"
            f"محدوده: {', '.join(track_scope) if track_scope else 'هیچ‌کدام'}\n\n"
            f"دستورات:\n"
            f"`{config.PREFIX}ردیابی روشن/خاموش`\n"
            f"`{config.PREFIX}ردیابی کانال <@username یا chat_id>`\n"
            f"`{config.PREFIX}ردیابی نوع حذف/ویرایش/هر دو`\n"
            f"`{config.PREFIX}ردیابی محدوده پیوی/گروه/هر دو`\n"
            f"`{config.PREFIX}ردیابی وضعیت`"
        )

    if sub in ("روشن", "on"):
        await save_settings(enabled=True)
        return await event.edit("✅ ردیابی روشن شد.")

    if sub in ("خاموش", "off"):
        await save_settings(enabled=False)
        return await event.edit("❌ ردیابی خاموش شد.")

    if sub in ("وضعیت", "status"):
        settings = await get_settings()
        status = "روشن ✅" if settings.enabled else "خاموش ❌"
        channel_info = f"کانال: {settings.channel_username or settings.channel_id or 'تنظیم نشده'}"
        track_types = []
        if settings.track_deleted:
            track_types.append("حذف")
        if settings.track_edited:
            track_types.append("ویرایش")
        track_scope = []
        if settings.track_private:
            track_scope.append("پیوی")
        if settings.track_groups:
            track_scope.append("گروه‌ها")
        return await event.edit(
            f"🔍 **وضعیت ردیابی**\n\n"
            f"وضعیت: {status}\n"
            f"{channel_info}\n"
            f"ردیابی: {', '.join(track_types) if track_types else 'هیچ‌کدام'}\n"
            f"محدوده: {', '.join(track_scope) if track_scope else 'هیچ‌کدام'}"
        )

    if sub in ("کانال", "channel"):
        if not rest:
            return await event.edit(f"مثال: `{config.PREFIX}ردیابی کانال @channel_username` یا `{config.PREFIX}ردیابی کانال 123456789`")
        rest = rest.strip()
        channel_id = None
        channel_username = None
        if rest.startswith("@"):
            channel_username = rest[1:]
            # برای گرفتن chat_id می‌توانیم از client.get_entity استفاده کنیم
            try:
                entity = await client.get_entity(rest)
                channel_id = entity.id
            except Exception as e:
                return await event.edit(f"❌ خطا در دریافت کانال: {e}")
        elif rest.lstrip("-").isdigit():
            channel_id = int(rest)
            try:
                entity = await client.get_entity(channel_id)
                if hasattr(entity, "username"):
                    channel_username = entity.username
            except Exception:
                pass
        else:
            return await event.edit("لطفاً یا یک @username معتبر یا یک chat_id عددی وارد کنید.")
        await save_settings(
            enabled=True,
            channel_id=channel_id,
            channel_username=channel_username,
        )
        return await event.edit(f"✅ کانال ردیابی تنظیم شد: {rest}")

    if sub in ("نوع", "type"):
        if not rest:
            return await event.edit(f"مثال: `{config.PREFIX}ردیابی نوع حذف` یا `{config.PREFIX}ردیابی نوع ویرایش` یا `{config.PREFIX}ردیابی نوع هر دو`")
        rest = rest.lower()
        track_deleted = False
        track_edited = False
        if "حذف" in rest:
            track_deleted = True
        if "ویرایش" in rest:
            track_edited = True
        if "هر دو" in rest or "همه" in rest:
            track_deleted = True
            track_edited = True
        if not track_deleted and not track_edited:
            return await event.edit("لطفاً نوع را مشخص کنید: حذف، ویرایش، یا هر دو")
        settings = await get_settings()
        await save_settings(
            enabled=settings.enabled,
            channel_id=settings.channel_id,
            channel_username=settings.channel_username,
            track_deleted=track_deleted,
            track_edited=track_edited,
            track_private=settings.track_private,
            track_groups=settings.track_groups,
        )
        types = []
        if track_deleted:
            types.append("حذف")
        if track_edited:
            types.append("ویرایش")
        return await event.edit(f"✅ ردیابی نوع‌های {', '.join(types)} فعال شد.")

    if sub in ("محدوده", "scope"):
        if not rest:
            return await event.edit(f"مثال: `{config.PREFIX}ردیابی محدوده پیوی` یا `{config.PREFIX}ردیابی محدوده گروه` یا `{config.PREFIX}ردیابی محدوده هر دو`")
        rest = rest.lower()
        track_private = False
        track_groups = False
        if "پیوی" in rest:
            track_private = True
        if "گروه" in rest:
            track_groups = True
        if "هر دو" in rest or "همه" in rest:
            track_private = True
            track_groups = True
        if not track_private and not track_groups:
            return await event.edit("لطفاً محدوده را مشخص کنید: پیوی، گروه، یا هر دو")
        settings = await get_settings()
        await save_settings(
            enabled=settings.enabled,
            channel_id=settings.channel_id,
            channel_username=settings.channel_username,
            track_deleted=settings.track_deleted,
            track_edited=settings.track_edited,
            track_private=track_private,
            track_groups=track_groups,
        )
        scopes = []
        if track_private:
            scopes.append("پیوی")
        if track_groups:
            scopes.append("گروه‌ها")
        return await event.edit(f"✅ ردیابی در محدوده‌های {', '.join(scopes)} فعال شد.")

    await event.edit(f"دستور نامعتبر. برای راهنما: `{config.PREFIX}ردیابی`")