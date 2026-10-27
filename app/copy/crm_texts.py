"""Persian copy for «📇 پیگیری‌ها» — the coach's follow-ups: who to call today,
who should renew, and the leads who asked about classes but never registered.

The admin-menu button label itself lives in copy/texts.py with the other menu
labels (BTN_ADMIN_CRM).
"""

# --- front page ---
TITLE = "📇 پیگیری‌ها"
FRONT_HINT = (
    "امروز با چه کسی تماس بگیری، چه کسی باید تمدید کند و "
    "سرنخ‌هایی که هنوز شاگرد نشده‌اند 👇"
)
BTN_TODAY = "⏰ امروز ({n})"
BTN_RENEWALS = "🔁 تمدید ({n})"
BTN_LEADS = "🧲 سرنخ‌ها ({n})"
BTN_NEW_LEAD = "➕ سرنخ جدید"
EXPIRED = "⌛ این دکمه دیگر معتبر نیست؛ از «📇 پیگیری‌ها» دوباره شروع کن 👇"

# --- relative dates ---
WHEN_TODAY = "امروز"
WHEN_TOMORROW = "فردا"
WHEN_OVERDUE = "🔴 {n} روز گذشته"
DAYS_AGO = "{n} روز پیش"
NO_END_DATE = "بی‌تاریخ"

# --- date shortcuts (add a follow-up, or push one back) ---
SHORTCUT_LABELS = {1: "فردا", 3: "۳ روز", 7: "یک هفته"}
BTN_OTHER_DATE = "📅 تاریخ دیگر"
ASK_DATE = "تاریخ پیگیری را به‌صورت شمسی بفرست (نمونه: 1405/08/20):"
INVALID_DATE = "⚠️ تاریخ درست نیست. نمونه: 1405/08/20"
NEEDS_TEXT = "⚠️ این‌جا فقط متن ذخیره می‌شود."

# --- today ---
TODAY_TITLE = "⏰ پیگیری‌های امروز"
TODAY_HINT = "موعدشان امروز است یا گذشته — روی هر مورد بزن 👇"
TODAY_EMPTY = "🟢 امروز پیگیری‌ای نداری."

# --- one follow-up ---
FU_TITLE = "⏰ پیگیری {name}"
LABEL_DUE = "موعد"
FU_IS_DONE = "✅ انجام شد — {date}"
FU_POSTPONE_HINT = "انجامش دادی؟ «✅ انجام شد» را بزن، یا عقبش بینداز 👇"
BTN_DONE = "✅ انجام شد"
BTN_OPEN_STUDENT = "👤 پروفایل {name}"
BTN_OPEN_LEAD = "🧲 سرنخ {name}"
FU_DONE = "✅ پیگیری {name} انجام شد."
FU_MOVED = "⏰ پیگیری {name} به {date} موکول شد."
FU_SAVED = "⏰ پیگیری برای {date} ثبت شد."

# --- a student's follow-ups (from the profile or a renewal) ---
BTN_FOLLOW_UP = "⏰ پیگیری"
PFU_TITLE = "⏰ پیگیری‌های {name}"
PFU_NONE = "پیگیری بازی ندارد."
PFU_HINT = "برای پیگیری تازه، تاریخش را بزن؛ اگر موضوعی دارد، اول متنش را بفرست 👇"
PFU_STAGED = "📝 موضوع آماده: {note}"
LABEL_NEXT_FOLLOW_UP = "پیگیری بعدی"

# --- a student's notes timeline ---
BTN_NOTES = "📝 یادداشت‌ها"
BTN_NOTES_COUNT = "📝 یادداشت‌ها ({n})"
BTN_NOTE = "📝 یادداشت"
NOTES_TITLE = "📝 یادداشت‌های {name}"
NOTES_EMPTY = "هنوز یادداشتی برایش ننوشته‌ای."
NOTES_HINT = "برای افزودن یادداشت، متنش را همین‌جا بفرست 👇"
NOTES_OLDER = "… و {n} یادداشت قدیمی‌تر"
NOTE_ENTRY = "🗓 {date}\n{text}"
NOTE_SAVED = "🟢 یادداشت ثبت شد."

# --- renewals ---
RENEWALS_TITLE = "🔁 تمدید"
RENEWALS_HINT = (
    "دوره‌شان تمام شده و هنوز دورهٔ تازه‌ای ندارند — تازه‌ترها بالاترند.\n"
    "🔔 هنوز پیگیری نشده · ✅ بعد از پایان دوره پیگیری شده"
)
RENEWALS_EMPTY = "🟢 کسی منتظر تمدید نیست."
RENEWAL_WAITING = "🔔"
RENEWAL_FOLLOWED = "✅"
CANDIDATE_TITLE = "🔁 تمدید {name}"
CANDIDATE_COURSE = "🏁 دورهٔ «{title}» — پایان: {date} ({ago})"
CANDIDATE_COURSE_NO_DATE = "🏁 دورهٔ «{title}» — بدون جلسهٔ ثبت‌شده"
CANDIDATE_WAITING = "🔔 از پایان دوره هنوز پیگیری نشده."
CANDIDATE_FOLLOWED = "✅ بعد از پایان دوره پیگیری شده."
LABEL_LAST_NOTE = "آخرین یادداشت"
BTN_PROFILE = "👤 پروفایل"
BTN_RENEW = "🔄 تمدید"
NOT_A_CANDIDATE = "🟢 «{name}» دیگر در فهرست تمدید نیست."

# --- leads ---
LEADS_TITLE = "🧲 سرنخ‌ها"
LEADS_HINT = "کسانی که دربارهٔ کلاس پرسیده‌اند و هنوز شاگرد نشده‌اند — روی هر نفر بزن 👇"
LEADS_EMPTY = "در این دسته سرنخی نیست."
STATUS_LABELS = {
    "NEW": "🆕 جدید",
    "CONTACTED": "📞 در تماس",
    "TRIAL": "🧪 آزمایشی",
    "WON": "🏆 شاگرد شد",
    "LOST": "❌ از دست رفت",
}
SOURCE_LABELS = {
    "INSTAGRAM": "📸 اینستاگرام",
    "TELEGRAM": "✈️ تلگرام",
    "REFERRAL": "🤝 معرفی",
    "WALK_IN": "🚶 حضوری",
    "WEBSITE": "🌐 وب‌سایت",
    "OTHER": "❔ سایر",
}

LEAD_TITLE = "🧲 سرنخ: {name}"
LABEL_STATUS = "وضعیت"
LABEL_PHONE = "شماره"
LABEL_SOURCE = "از طریق"
LABEL_INTEREST = "علاقه"
LABEL_NOTE = "یادداشت‌ها"
LABEL_CREATED = "ثبت"
LEAD_PHONE_KNOWN = (
    "ℹ️ این شماره مال شاگرد «{name}» است؛ «✅ تبدیل به شاگرد» سرنخ را به همو وصل می‌کند."
)
LEAD_WON = "🏆 شاگرد شد: {name}"
LEAD_FOLLOW_UP_HINT = "⏰ برای تعیین پیگیری بعدی یکی از تاریخ‌ها را بزن 👇"
LEAD_NOTE_LINE = "{date} — {text}"
NOTE_CLIPPED = "…"
BTN_LEAD_NOTE = "📝 یادداشت"
BTN_LEAD_PHONE = "📞 شماره"
BTN_LEAD_FOLLOW_UP_DONE = "✅ پیگیری انجام شد"
BTN_CONVERT = "✅ تبدیل به شاگرد"
BTN_LOST = "❌ از دست رفت"
BTN_DELETE_LEAD = "🗑 حذف سرنخ"
BTN_CLEAR_PHONE = "➖ حذف شماره"

ASK_LEAD_NAME = "نام کسی را که دربارهٔ کلاس پرسیده بفرست:"
ASK_LEAD_PHONE = "شماره موبایلش را بفرست (یا «⏭ رد کردن»):"
ASK_LEAD_SOURCE = "«{name}» از کجا با تو آشنا شده؟"
ASK_LEAD_INTEREST = (
    "به چه چیزی علاقه دارد؟ (مثلاً «کلاس فیتنس» یا «برنامه غذایی») — یا «⏭ رد کردن»:"
)
LEAD_SAVED = "🟢 سرنخ ثبت شد."
ASK_LEAD_NOTE = "یادداشت تازه برای «{name}» را بفرست — با تاریخ امروز ثبت می‌شود:"
ASK_LEAD_PHONE_EDIT = "شمارهٔ «{name}» را بفرست:"
ASK_LEAD_PHONE_EDIT_CLEAR = "شمارهٔ تازهٔ «{name}» را بفرست، یا «➖ حذف شماره» را بزن:"
PHONE_SAVED = "🟢 شماره ذخیره شد."
PHONE_CLEARED = "🟢 شماره حذف شد."
STATUS_SAVED = "🟢 وضعیت: {status}"
LEAD_LOST = "❌ «{name}» از دست رفته ثبت شد؛ پیگیری بازش بسته شد."
LEAD_FOLLOW_UP_DONE = "✅ پیگیری «{name}» انجام شد."
CONFIRM_CONVERT = "✅ «{name}» شاگرد شود؟\nحضوری است یا غیرحضوری؟"
CONVERTED = "🟢 «{name}» شاگرد شد."
CONVERT_LINKED = "🔗 این شماره قبلاً برای «{name}» ثبت شده بود؛ سرنخ به همین شاگرد وصل شد."
CONFIRM_DELETE_LEAD = (
    "⚠️ سرنخ «{name}» حذف شود؟\nیادداشت‌ها و پیگیری‌هایش هم پاک می‌شوند و بازگشت‌پذیر نیست."
)
LEAD_DELETED = "🗑 سرنخ «{name}» حذف شد."

# Written on the student's timeline when a lead becomes a student.
CONVERTED_NOTE = "🧲 از سرنخ شاگرد شد — از طریق {source}"
CONVERTED_NOTE_INTEREST = "علاقه: {interest}"

# --- errors raised by services/crm.py ---
ERR_NAME_REQUIRED = "نام الزامی است"
ERR_NAME_TOO_LONG = "نام طولانی است (حداکثر {n} حرف)"
ERR_INTEREST_TOO_LONG = "متن علاقه طولانی است (حداکثر {n} حرف)"
ERR_PHONE_INVALID = "شماره موبایل نامعتبر است"
ERR_NOTE_EMPTY = "یادداشت خالی است"
ERR_LEAD_NOT_FOUND = "سرنخ مورد نظر یافت نشد"
ERR_FOLLOW_UP_NOT_FOUND = "پیگیری مورد نظر یافت نشد"
ERR_FOLLOW_UP_TARGET = "پیگیری یا برای یک شاگرد است یا برای یک سرنخ"
ERR_FOLLOW_UP_DONE = "این پیگیری قبلاً انجام شده است"
ERR_DUE_RANGE = "تاریخ پیگیری باید از امروز تا یک سال بعد باشد — سال شمسی را بررسی کن"
ERR_LEAD_CLOSED = "این سرنخ بسته است؛ برای پیگیری، اول وضعیتش را عوض کن"
ERR_LEAD_CONVERTED = "این سرنخ شاگرد شده است"
ERR_USE_CONVERT = "برای «شاگرد شد» از «✅ تبدیل به شاگرد» استفاده کن"

# --- the coach's morning digest (notifications/digest.py) ---
DIGEST = "📇 پیگیری‌های امروز: ⏰ {due} · 🔁 {renewals} تمدید · 🧲 {leads} سرنخ"
