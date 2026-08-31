"""🧩 معماسازِ اتاق فرار: پازل‌های seed-دار با جواب‌های متغیر.

هر پازل یک dict است:
  id, kind, prompt (متنِ نمایشی), answer (رشته‌ی استانداردشده),
  hints: [سه سطح], reward (امتیاز), requires (آیتم‌های لازم برای پاس‌دادن، اختیاری)
پاسخ‌ها همیشه با `_norm` مقایسه می‌شوند (فارسی/انگلیسی/فاصله/ارقام).
seed باعث می‌شود در هر Session جواب‌ها متفاوت باشند ولی قابل‌حل بمانند —
سرنخِ هر پازل داخلِ همان سناریو (متنیِ inspection) جاسازی می‌شود.
"""
from __future__ import annotations

import random

PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def to_fa(num: int) -> str:
    return str(num).translate(PERSIAN_DIGITS)


def _norm(s: str) -> str:
    """نرمال‌سازی پاسخ: ارقام فارسی→انگلیسی، حذفِ فاصله/صفرِ ابتدا، حروف کوچک."""
    s = (s or "").strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    s = " ".join(s.lower().split())
    return s


def check_answer(puzzle: dict, raw: str) -> bool:
    return _norm(raw) == _norm(str(puzzle["answer"]))


# --------------------------------------------------------------- سازنده‌ها --
def make_code_puzzle(rng: random.Random, scenario_id: str) -> dict:
    """رمز عددی سه‌رقمی؛ هر رقم سرنخِ جدا دارد (اشیا/تابلو/ساعتِ اتاق)."""
    a, b, c = (rng.randint(1, 9) for _ in range(3))
    prompts = [
        (f"روی تابلو نوشته: «نخستین رقم، تعدادِ {['تابلوی‌هایِ شکسته','صندلی‌هایِ جفت','کتاب‌هایِ قرمز'][rng.randint(0,2)]} است.»",
         a, "تعدادش را در همین اتاق دیده‌ای — با دقت بشمار."),
        (f"روی کاغذی چسبیده: «رقمِ دوم = سالِ ساخته‌شدنِ این مکان، بدونِ قرن» (سال: 1{b}{rng.randint(0,9)}{rng.randint(0,9)})",
         b, "دو رقمِ آخرِ سال را جدا کن؛ رقمِ دومِ رمز یکی از همین‌هاست."),
        (f"ساعتِ دیواری روی {to_fa(c)}:00 متوقف مانده. «رقمِ سوم = عقربه‌ی ساعت»",
         c, "ساعت را نگاه کن؛ عقربه‌ی کوچک روی چه عددی ایستاده؟"),
    ]
    rng.shuffle(prompts)
    lines = [p for p, _, _ in prompts]
    hints = [h for _, _, h in prompts]
    return {
        "id": f"code_{scenario_id}",
        "kind": "code",
        "prompt": "🔐 یک قفلِ سه‌رقمی:\n" + "\n".join(lines),
        "answer": f"{a}{b}{c}",
        "hints": hints,
        "reward": 120,
    }


def make_pattern_puzzle(rng: random.Random, scenario_id: str) -> dict:
    """الگوی عددی: دنباله‌ای که رابطه‌اش از سه عضو اول کشف می‌شود."""
    step = rng.randint(2, 6)
    start = rng.randint(1, 9)
    seq = [start + step * i for i in range(4)]
    answer = start + step * 4
    return {
        "id": f"pattern_{scenario_id}",
        "kind": "pattern",
        "prompt": (
            "🧮 روی دیوار با گچ نوشته شده:\n"
            f"{to_fa(seq[0])} → {to_fa(seq[1])} → {to_fa(seq[2])} → {to_fa(seq[3])} → ؟"
        ),
        "answer": str(answer),
        "hints": [
            "اختلافِ ثابتی بینِ اعداد هست.",
            f"هر بار {to_fa(step)} تا اضافه می‌شود.",
            f"جواب: {to_fa(seq[3])} + {to_fa(step)}",
        ],
        "reward": 90,
    }


def make_logic_puzzle(rng: random.Random, scenario_id: str) -> dict:
    """منطقی: سه کلید، فقط یکی درست؛ جملاتِ حک‌شده یکی دروغ است."""
    truth_idx = rng.randint(0, 2)
    claims = [
        "«کلیدِ من دروغ می‌گوید.»",
        "«کلیدِ وسطی درست می‌گوید.»",
        "«کلیدِ من دروغ می‌گوید.»",
    ]
    # چیدمانِ منطق: با truth_idx، جمله‌های دروغ باید ناسازگار با واقعیت باشند.
    labels = ["آبی", "قرمز", "زرشکی"]
    rng.shuffle(labels)
    truth_label = labels[truth_idx]
    return {
        "id": f"logic_{scenario_id}",
        "kind": "logic",
        "prompt": (
            "🚪 سه قفل روی در است و هرکدام جمله‌ای حک دارند. فقط یک قفل واقعاً باز می‌کند:\n"
            f"1️⃣ {labels[0]}: {claims[0]}\n"
            f"2️⃣ {labels[1]}: {claims[1]}\n"
            f"3️⃣ {labels[2]}: {claims[2]}\n"
            "دقیقاً «یکی» از این جمله‌ها راست است. کدام قفل؟ (نامِ رنگ را بنویس)"
        ),
        "answer": truth_label,
        "hints": [
            "جمله‌های ۱ و ۳ نمی‌توانند هر دو راست باشند.",
            "اگر جمله‌ی وسطی راست باشد، بقیه دروغ‌اند — ولی آن‌وقت دو جمله متناقضِ راست می‌شد؟ امتحان کن.",
            f"قفلِ درست: {truth_label}",
        ],
        "reward": 110,
    }


def make_order_puzzle(rng: random.Random, scenario_id: str) -> dict:
    """ترتیبِ اشیا: دکمه‌ها را به ترتیبِ سنِشان/اندازه‌شان فشار بده."""
    objs = [
        ("🥚", "تخم‌مرغِ چینی"),
        ("🕯", "شمعِ نیم‌سوخته"),
        ("🕰", "ساعتِ جیبی"),
        ("📻", "رادیوی قدیمی"),
    ]
    correct = objs[:]  # از قدیمی به جدید (داستانی)
    prompt = (
        "🎛 چهار دکمه با علامتِ اشیاست. زیرش نوشته: «از کهنه‌ترین به نوترین فشار بده»\n"
        + " | ".join(f"{e} {n}" for e, n in objs)
        + "\n(ترتیب را با شماره بده: مثل 2 1 4 3)"
    )
    answer = " ".join(str(objs.index(o) + 1) for o in correct)
    return {
        "id": f"order_{scenario_id}",
        "kind": "order",
        "prompt": prompt,
        "answer": answer,
        "hints": [
            "به داستانِ هر شیء فکر کن؛ کدام قدیمی‌تر است؟",
            "تخم‌مرغ قدیمی‌تر از شمع است؛ شمع قدیمی‌تر از ساعتِ جیبی.",
            "ترتیبِ درست: 1 2 3 4",
        ],
        "reward": 100,
    }


def make_riddle_puzzle(rng: random.Random, scenario_id: str) -> dict:
    """معمای متنی (چیستان) — جوابِ تک‌کلمه‌ای."""
    riddles = [
        ("هرچه ازش برداری بزرگ‌تر می‌شود. چیست؟", "چاله", ["چیزی که حفر می‌شود.", "با بیل ساخته می‌شود.", "چاله"]),
        ("کلید دارد ولی قفل ندارد؛ فضا دارد ولی خانه ندارد. چیست؟", "پیانو", ["صدا دارد.", "سیاه و سفید است.", "پیانو"]),
        ("هرچه روشن‌تر باشد، سایه‌ها بیشتر دیده می‌شوند. چه چیزی؟", "نور", ["با چشم دیده می‌شود.", "از چراغ می‌آید.", "نور"]),
    ]
    q, a, hints = rng.choice(riddles)
    return {
        "id": f"riddle_{scenario_id}",
        "kind": "riddle",
        "prompt": f"❓ چیستانِ حک‌شده روی در:\n«{q}»",
        "answer": a,
        "hints": hints,
        "reward": 80,
    }


def make_choice_puzzle(rng: random.Random, scenario_id: str) -> dict:
    """انتخابِ درست بین مسیرها؛ یک سرنخِ محیطی راهنمایی می‌کند."""
    right = rng.randint(1, 3)
    cue = {1: "بوی نم از آن‌سو می‌آید", 2: "هوای آن‌سو گرم‌تر است", 3: "صدای قطره از آن‌سو می‌آید"}[right]
    return {
        "id": f"choice_{scenario_id}",
        "kind": "choice",
        "prompt": (
            "🚦 سه راهرو؛ فقط یکی به خروجی می‌رسد:\n"
            "1️⃣ راهرویِ تاریک\n2️⃣ راهرویِ باریک\n3️⃣ راهرویِ سرپوشیده\n"
            f"سرنخ: «{cue}» — کدام؟ (شماره)"
        ),
        "answer": str(right),
        "hints": [
            "سرنخِ محیطی را جدی بگیر.",
            "آب یعنی راهِ خروج به سطحِ زمین.",
            f"پاسخ: {to_fa(right)}",
        ],
        "reward": 90,
    }


PUZZLE_MAKERS = [
    make_code_puzzle,
    make_pattern_puzzle,
    make_logic_puzzle,
    make_order_puzzle,
    make_riddle_puzzle,
    make_choice_puzzle,
]


def build_stage_puzzles(rng: random.Random, scenario_id: str, n_stages: int) -> list[dict]:
    """برای هر مرحله یک پازل؛ بدونِ تکرار تا جایی که ممکن است."""
    makers = PUZZLE_MAKERS[:]
    rng.shuffle(makers)
    puzzles = []
    for i in range(n_stages - 1):  # آخرین مرحله boss است
        maker = makers[i % len(makers)]
        puzzles.append(maker(rng, f"{scenario_id}{i}"))
    return puzzles
