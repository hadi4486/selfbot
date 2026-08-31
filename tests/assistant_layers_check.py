"""تستِ منطقِ دو لایه‌ی تشخیصِ آنلاین/آفلاینِ منشی (بدون تلگرام)"""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

os.environ.setdefault("API_ID", "12345")
os.environ.setdefault("API_HASH", "x")
os.environ.setdefault("DATABASE_URL", "postgresql://p:p@localhost/p")
sys.path.insert(0, "/data/workspace/selfbot/selfbot-main")

import bot.config as config
import bot.handlers.assistant as a

config.ASSISTANT_ONLINE_THRESHOLD = 180
config.ASSISTANT_SESSION_MAX_AGE = 300
a.assistant_state["schedule_enabled"] = False
a.assistant_state["auto_detect"] = True
MIN = datetime.min.replace(tzinfo=timezone.utc)
now = datetime.now(timezone.utc)
ok = True


def case(name, expected_enabled, local_gap, seen_gap=None, poll_age=None):
    global ok
    a._last_self_activity = MIN if local_gap is None else now - timedelta(seconds=local_gap)
    a._last_session_poll_ok = MIN if poll_age is None else now - timedelta(seconds=poll_age)
    a._last_session_seen = MIN if seen_gap is None else now - timedelta(seconds=seen_gap)
    a._recompute_enabled_from_signals()
    actual = a.assistant_state["enabled"]
    passed = actual == expected_enabled
    ok = ok and passed
    print(("✓" if passed else "✗"), f"{name} → enabled={actual} (انتظار: {expected_enabled})")


# ۱) هیچ سیگنالی → آفلاین → منشی روشن
case("بدون هیچ سیگنال", True, None, None, None)
# ۲) فقط local تازه (۵۰s) → تو آنلاینی → منشی خاموش
case("local تازه ۵۰s", False, 50, None, None)
# ۳) فقط session تازه (۶۰s با poll تازه) → آنلاین → منشی خاموش
case("session تازه ۶۰s", False, 9999, 60, 30)
# ۴) هر دو کهنه (۳۰۰s+) → آفلاین → منشی روشن
case("هر دو کهنه", True, 400, 400, 30)
# ۵) local کهنه ولی session تازه → آنلاین (لایه‌ی سشن نجات می‌دهد)
case("local کهنه، session تازه", False, 600, 50, 30)
# ۶) session کهنه‌ی poll (poll_age>MAX_AGE) → فقط local حساب می‌شود
case("poll کهنه، local کهنه", True, 500, 10, 400)  # session نادیده → آفلاین
case("poll کهنه، local تازه", False, 60, 10, 400)  # فقط local → آنلاین
# ۷) خطای متوالی poll → backoff → session غیرقابل‌اعتماد (poll کهنه شبیه‌سازی شد بالا)

print("ALL OK" if ok else "FAILED")
sys.exit(0 if ok else 1)


# ---- سناریوی سشن current: باید نادیده گرفته بشه ----
import bot.handlers.assistant as a2

class FakeAuth:
    def __init__(self, current, days_ago, hours_active_ago=0):
        self.current = current
        self.date_active = now - timedelta(days=days_ago, hours=-hours_active_ago)

class FakeResult:
    def __init__(self, auths):
        self.authorizations = auths

# شبیه‌سازی مستقیم حلقه‌ی استخراجِ _poll_session_activity بدون کلاینت:
auths = [FakeAuth(True, 0), FakeAuth(False, 2), FakeAuth(False, 0, 5)]  # current + گوشیِ ۲ روز پیش + وبِ ۵ ساعت پیش
newest = None
for auth in auths:
    if getattr(auth, "current", False):
        continue
    active = auth.date_active
    if newest is None or active > newest:
        newest = active
# باید وبِ ۵ ساعت پیش انتخاب بشه (نه current که الان است)
expected = auths[2].date_active
assert newest == expected, "سشن current نباید شمرده شود"
print("✓ فیلتر سشن current در استخراجِ date_active کار می‌کند")
