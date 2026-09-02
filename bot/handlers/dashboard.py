"""📊 داشبورد شخصی: نمایِ یکجای همه‌ی سیستم‌ها (`.داشبورد`)."""
import datetime as dt

from telethon import events

from ..config import PREFIX, TIMEZONE_OFFSET
from ..health import get_uptime
from ..repositories import escape_repo, inbox_repo, tasks_repo
from ..runtime import client
from ..storage.scheduler_store import list_jobs
from ..storage.settings_toggles import toggles
from ..storage.stats_store import STATS
from ..utils import pat


def _fmt_uptime() -> str:
    try:
        return get_uptime()
    except Exception:
        return "—"


@client.on(events.NewMessage(outgoing=True, pattern=pat(["داشبورد", "dashboard"])))
async def dashboard_handler(event):
    await event.edit("📊 در حال جمع‌کردنِ داشبورد...")

    # اینباکس
    try:
        ib = await inbox_repo.get_stats()
        ib_imp = ib.get("important", 0)
        ib_unread = ib.get("unread", 0)
    except Exception:
        ib_imp = ib_unread = 0

    # کارها
    try:
        open_tasks = await tasks_repo.list_tasks(done=False, limit=200)
        overdue = sum(
            1 for t in open_tasks if t["due_at"] and (t["due_at"] if t["due_at"].tzinfo else t["due_at"].replace(tzinfo=dt.timezone.utc)) < dt.datetime.now(dt.timezone.utc)
        )
    except Exception:
        open_tasks, overdue = [], 0

    # یادآوری‌های پیش‌رو
    try:
        reminders = await list_jobs("reminder")
    except Exception:
        reminders = []

    # بازی
    try:
        esc = await escape_repo.stats_summary()
        games = esc.get("most_solved", 0) if isinstance(esc, dict) else 0
        wins = esc.get("top_score", 0) if isinstance(esc, dict) else 0
    except Exception:
        games = wins = 0

    msgs = STATS.get("messages_total", 0)
    cmds = STATS.get("commands_total", 0)
    errors = STATS.get("errors", 0) if isinstance(STATS, dict) and "errors" in STATS else 0

    auto = "🟢 روشن" if toggles.get("autopilot_enabled", False) else "🔴 خاموش"
    local_now = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=TIMEZONE_OFFSET)

    lines = [
        "╭────── 🤖 دستیارِ شخصی ──────╮",
        "",
        f"🕐 {local_now.strftime('%Y-%m-%d %H:%M')}  |  ⏱ {_fmt_uptime()}",
        "",
        f"📨 پیام‌ها: {msgs:,}  |  ⌨️ دستورها: {cmds:,}",
        f"📥 اینباکس: {ib_unread} خوانده‌نشده • {ib_imp} مهم",
        f"📝 کارهای باز: {len(open_tasks)}  |  ⏰ عقب‌افتاده: {overdue}",
        f"🔔 یادآوری‌های فعال: {len(reminders)}",
        f"🤖 اتوپایلوت: {auto}",
        f"🎮 اتاقِ فرار: {games} اتاق حل‌شده • رکوردِ امتیاز: {wins:,}",
        f"⚠️ خطاها: {errors}",
        "",
        f"╰─ `{PREFIX}پنل` برای همه‌ی دستورها ─╯",
    ]
    await event.edit("\n".join(lines))
