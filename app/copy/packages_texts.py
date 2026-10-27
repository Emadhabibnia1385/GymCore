"""Persian strings for «📦 پکیج‌ها» — reusable program bundles.

A package is the coach's course material (a diet PDF, training videos, text)
built once and sent to any number of students. Admin screens, the student's
side and the service's messages all take their wording from here.
"""

PLATFORM_LABELS = {"TELEGRAM": "تلگرام", "BALE": "بله"}

# What an item is, at a glance (icon) and in words.
KIND_ICONS = {"video": "🎬", "photo": "🖼", "document": "📎", "text": "📝"}
KIND_NAMES = {"video": "ویدیو", "photo": "عکس", "document": "فایل", "text": "متن"}

# --- the «📄 مدیریت برنامه‌ها» hub ---
BTN_PACKAGES = "📦 پکیج‌ها"
HUB_HINT = (
    "📦 پکیج: برنامهٔ غذایی، ویدیوهای تمرین و متن، با هم — یک بار بساز و برای "
    "هر چند شاگرد که خواستی بفرست."
)

# --- packages list ---
LIST_TITLE = "📦 پکیج‌ها"
LIST_HINT = "روی هر پکیج بزن تا آیتم‌ها و گیرندگانش را ببینی 👇"
NO_PACKAGES = "هنوز پکیجی نساختی. با «➕ پکیج جدید» اولی را بساز."
BTN_NEW = "➕ پکیج جدید"
LIST_ROW = "{dot} {title} · {n} مورد · 👥 {r}"

# --- creating / editing a package ---
ASK_TITLE = "عنوان پکیج را بفرست (مثلاً «پکیج کاهش وزن ۸ هفته‌ای»):"
ASK_DESCRIPTION = (
    "توضیح پکیج را بفرست — شاگرد آن را بالای آیتم‌ها می‌بیند — یا «⏭ رد کردن» "
    "(یا همین حالا اولین فایلش را بفرست):"
)
ASK_SET_DESCRIPTION = "توضیح پکیج را بفرست — شاگرد آن را بالای آیتم‌ها می‌بیند:"
ASK_NEW_TITLE = "عنوان فعلی: {current}\n\nعنوان تازه را بفرست:"
ASK_NEW_DESCRIPTION = "توضیح فعلی:\n{current}\n\nتوضیح تازه را بفرست:"
BTN_CLEAR_DESCRIPTION = "➖ حذف توضیح"
CREATED = "🟢 پکیج ساخته شد. حالا آیتم‌هایش را اضافه کن 👇"
SAVED = "🟢 ذخیره شد."
STEP_EXPIRED = "⌛ این مرحله دیگر فعال نیست؛ از «📦 پکیج‌ها» دوباره شروع کن 👇"

# --- one package ---
STATUS_ACTIVE = "🟢 فعال"
STATUS_INACTIVE = "⚪ غیرفعال — شاگردان نمی‌بینندش"
RECIPIENTS_COUNT = "👥 {n} گیرنده"
ITEMS_HEADER = "آیتم‌ها ({n}):"
NO_ITEMS = "هنوز آیتمی ندارد — با «➕ افزودن آیتم» فایل یا متن اضافه کن."
ITEMS_HINT = "روی هر آیتم بزن تا ترتیب، متن یا نسخهٔ پیام‌رسان دیگرش را تنظیم کنی 👇"
MISSING_COPIES = (
    "📲 {n} فایل هنوز نسخهٔ {platform} ندارد؛ شاگردانِ {platform} فعلاً فقط متنش را می‌گیرند."
)
AVAILABILITY = "{tg} {tg_mark} · {bale} {bale_mark}"
BTN_ADD_ITEM = "➕ افزودن آیتم"
BTN_SEND = "📤 ارسال به شاگردان"
BTN_RECIPIENTS = "👥 گیرندگان ({n})"
BTN_EDIT_TITLE = "✏️ عنوان"
BTN_EDIT_DESCRIPTION = "✏️ توضیح"
BTN_ACTIVATE = "🟢 فعال کن"
BTN_DEACTIVATE = "⚪ غیرفعال کن"
BTN_DELETE = "🗑 حذف پکیج"
ACTIVATED = "🟢 پکیج فعال شد؛ گیرندگانش دوباره می‌بینندش."
DEACTIVATED = "⚪ پکیج غیرفعال شد و از «برنامه‌های من» شاگردان پنهان است."
DELETE_CONFIRM = "⚠️ پکیج «{title}» و همهٔ آیتم‌هایش حذف شود؟"
DELETED = "🗑 پکیج حذف شد."

# --- adding items ---
ASK_ITEM = (
    "فایل آیتم را بفرست — PDF، عکس یا ویدیو؛ کپشنش متن آیتم می‌شود — یا متنش را بنویس.\n"
    "چند فایل پشت سر هم هم می‌شود؛ آخر کار «✅ تمام» را بزن."
)
ITEM_ADDED = (
    "🟢 «{label}» اضافه شد — این پکیج حالا {n} آیتم دارد.\n"
    "آیتم بعدی را بفرست، یا «✅ تمام»."
)
BTN_DONE_ADDING = "✅ تمام"

# --- one item ---
ITEM_TITLE = "📦 {package} — آیتم {pos} از {total}"
LABEL_ITEM_TITLE = "🏷 عنوان"
LABEL_ITEM_TEXT = "📝 متن"
EMPTY_VALUE = "—"
TEXT_EVERYWHERE = "📲 متن است؛ در تلگرام و بله هر دو می‌رسد."
BTN_EDIT_TEXT = "✏️ متن"
BTN_EDIT_ITEM_TITLE = "🏷 عنوان"
BTN_COPY = "📲 نسخهٔ {platform}"
BTN_ADD_COPY_HERE = "📲 افزودن نسخهٔ {platform}"
BTN_DELETE_ITEM = "🗑 حذف آیتم"
ASK_ITEM_TEXT = "متن فعلی:\n{current}\n\nمتن تازه را بفرست:"
BTN_CLEAR_TEXT = "➖ حذف متن"
ASK_ITEM_TITLE = (
    "عنوانی را بفرست که شاگرد روی دکمهٔ این آیتم می‌بیند.\nعنوان فعلی: {current}"
)
BTN_CLEAR_TITLE = "➖ حذف عنوان"
ITEM_DELETE_CONFIRM = "⚠️ آیتم «{label}» از این پکیج حذف شود؟"
ITEM_DELETED = "🗑 آیتم حذف شد."

# --- the other messenger's copy of a file ---
COPY_HOWTO = (
    "📲 این فایل در {have} هست، ولی در {missing} نه.\n\n"
    "برای این‌که شاگردانِ {missing} هم بگیرندش، در ربات {missing} برو به "
    "⚙️ پنل مدیریت ← 📄 مدیریت برنامه‌ها ← 📦 پکیج‌ها ← همین پکیج ← همین آیتم، "
    "«📲 افزودن نسخهٔ {missing}» را بزن و همین فایل را بفرست."
)
ASK_COPY = "همین {kind} را این‌جا بفرست تا شاگردانِ {platform} هم بگیرندش:"
COPY_SAVED = "🟢 نسخهٔ {platform} ثبت شد."

# --- sending to students ---
ASK_PICK = (
    "📤 ارسال «{title}» — شاگردها را انتخاب کن (🌐 غیرحضوری‌ها بالاترند)، "
    "یا نامی بفرست تا فهرست کوتاه شود:"
)
PICK_FILTER = "🔎 «{query}»"
PICK_NONE = "شاگردی با این مشخصات پیدا نشد."
PICK_SELECTED = "انتخاب‌شده: {n} نفر"
PICK_ROW = "{dot} {icon} {name}"
PICK_HAS = "✅ {icon} {name} — دارد"
BTN_SEND_TO = "✅ ارسال برای {n} نفر"
BTN_SHOW_ALL = "🔄 همهٔ شاگردان"
PICK_EXPIRED = "⌛ انتخاب‌ها از دست رفت؛ دوباره انتخاب کن."
SENT = "🟢 پکیج برای {n} شاگرد فعال شد و خبرش برایشان رفت."
SENT_NOBODY_NEW = "این شاگردان پکیج را از قبل داشتند."

# --- recipients ---
RECIPIENTS_TITLE = "👥 گیرندگان «{title}» — {n} نفر"
RECIPIENTS_HINT = "روی نام بزن تا برنامه‌های آن شاگرد باز شود · 🚫 برداشتن دسترسی"
NO_RECIPIENTS = "هنوز برای کسی نفرستادی."
RECIPIENT_ROW = "👤 {name}"
BTN_REVOKE = "🚫"
REVOKE_CONFIRM = (
    "⚠️ دسترسی «{name}» به پکیج «{title}» برداشته شود؟\n"
    "پکیج از «برنامه‌های من» او پنهان می‌شود."
)
BTN_YES_REVOKE = "🚫 بله، بردار"
REVOKED = "🟢 دسترسی {name} به «{title}» برداشته شد."

# --- one student's packages (from their programs screen) ---
BTN_GIVE = "📦 ارسال پکیج"
CLIENT_PACKAGE_ROW = "📦 {title}"
CLIENT_PACKAGE_INACTIVE = "📦 {title} ⚪"
CLIENT_PACKAGES_HINT = "📦 پکیج‌ها: روی هر کدام بزن تا صفحه‌اش باز شود · 🚫 برداشتن دسترسی"
ASK_PICK_PACKAGE = "📦 پکیج برای «{name}» — یکی را انتخاب کن:"
PICK_PACKAGE_ROW = "📦 {title} · {n} مورد"
PICK_PACKAGE_HAS = "✅ {title} — دارد"
NO_ACTIVE_PACKAGES = "هنوز پکیج فعالی نداری؛ اول از «📦 پکیج‌ها» یکی بساز."
GIVEN = "🟢 پکیج «{title}» برای {name} فعال شد و خبرش برایش رفت."
ALREADY_HAS = "«{name}» این پکیج را از قبل دارد."

# --- the student's side ---
STUDENT_PACKAGE_ROW = "📦 {title} · {n} مورد"
STUDENT_PACKAGE_HINT = "روی هر مورد بزن تا برایت ارسال شود 👇"
STUDENT_PACKAGE_EMPTY = "هنوز موردی در این پکیج نیست."
ITEM_SENT = "🟢 «{label}» برایت ارسال شد. مورد بعدی را انتخاب کن 👇"
FILE_ON_OTHER = "📲 فایل این مورد فعلاً فقط در {platform} است؛ از ربات {platform} بازش کن."
FILE_FAILED = "⚠️ فایل این مورد ارسال نشد؛ به مربی خبر بده."
NOTIFY_ASSIGNED = "📦 پکیج «{title}» برایت فعال شد 🟢\nاز «📄 برنامه‌های من» ببینش."

# --- service refusals (the admin screens put ⚠️ in front) ---
NOT_FOUND = "پکیج یافت نشد"
ITEM_NOT_FOUND = "آیتم یافت نشد"
ASSIGNMENT_NOT_FOUND = "این دسترسی یافت نشد"
TITLE_REQUIRED = "عنوان پکیج الزامی است"
TITLE_TOO_LONG = "عنوان حداکثر {n} حرف باشد"
DESCRIPTION_TOO_LONG = "توضیح حداکثر {n} حرف باشد"
ITEM_LIMIT = "هر پکیج حداکثر {n} آیتم دارد؛ برای بیشتر، پکیج دیگری بساز."
ITEM_TEXT_REQUIRED = "آیتم متنی باید متن داشته باشد"
ITEM_KIND_INVALID = "نوع آیتم نامعتبر است"
ITEM_UNSUPPORTED = "این را نمی‌شود آیتم کرد — PDF، عکس، ویدیو یا متن بفرست."
FILE_REQUIRED = "این‌جا خودِ فایل لازم است."
COPY_WRONG_KIND = "این آیتم {kind} است — همان را به شکل {kind} بفرست."
SEND_INACTIVE = "این پکیج غیرفعال است؛ اول فعالش کن، بعد بفرست."
SEND_EMPTY = "این پکیج هنوز آیتمی ندارد؛ اول آیتم اضافه کن، بعد بفرست."
DELETE_REFUSED = (
    "این پکیج برای شاگردان فرستاده شده؛ حذفش نکن — غیرفعالش کن تا از برنامه‌هایشان "
    "پنهان شود."
)
