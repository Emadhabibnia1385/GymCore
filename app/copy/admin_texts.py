"""Centralized Persian strings for the in-bot admin panel."""

# --- generic ---
BACK = "🔙 بازگشت"
CANCEL = "✖️ لغو"
CONFIRM = "✅ تأیید"
SKIP = "⏭ رد کردن"
DONE = "✅ انجام شد"
PREV = "◀️"
NEXT = "▶️"
CANCELLED = "لغو شد."
SAVED = "🟢 با موفقیت ثبت شد."
NOTHING = "موردی برای نمایش نیست."
INVALID_NUMBER = "لطفاً یک عدد معتبر وارد کن."
INVALID_DATE = "تاریخ نامعتبر است. نمونه: 1405/04/28"

# --- students ---
STUDENTS_TITLE = "👥 مدیریت شاگردان"
STUDENTS_HINT = "برای جست‌وجو، نام یا شماره یا آیدی عددی را بفرست، یا از فهرست انتخاب کن:"
BTN_NEW_STUDENT = "➕ شاگرد جدید"
BTN_SEARCH = "🔎 جست‌وجو"
ASK_STUDENT_NAME = "نام و نام خانوادگی شاگرد را بفرست:"
ASK_STUDENT_PHONE = "شماره موبایل را بفرست (یا «⏭ رد کردن»):"
STUDENT_CREATED = "🟢 شاگرد ثبت شد."
PROFILE = "پروفایل شاگرد"
BTN_COURSES = "📚 دوره‌ها"
BTN_PROGRAMS = "📄 برنامه‌ها"
BTN_ATTENDANCE = "✅ حضور و غیاب"
BTN_PAYMENTS = "💳 پرداخت‌ها"
BTN_PAUSE = "⏸ غیرفعال‌سازی"
BTN_ACTIVATE = "🟢 فعال‌سازی"
BTN_DELETE_STUDENT = "🗑 حذف شاگرد"
BTN_YES_DELETE = "🗑 بله، حذف کن"
CONFIRM_DELETE_STUDENT = (
    "⚠️ «{name}» حذف شود؟\n"
    "همهٔ دوره‌ها، پرداخت‌ها و برنامه‌های او هم حذف می‌شوند و بازگشت‌پذیر نیست."
)
LABEL_PHONE = "شماره"
LABEL_STATUS = "وضعیت"
LABEL_ACTIVE = "فعال"
LABEL_INACTIVE = "غیرفعال"
NO_STUDENTS = "هنوز شاگردی ثبت نشده است."

# --- classes ---
CLASSES_TITLE = "🏋️ مدیریت کلاس‌ها"
CLASSES_HINT = "روی عنوان بزن تا فعال/غیرفعال شود · ✏️ ویرایش · 🗑 حذف"
BTN_NEW_CLASS = "➕ کلاس جدید"
ASK_CLASS_TITLE = "عنوان کلاس را بفرست:"
BTN_ENABLE = "🟢 فعال"
BTN_DISABLE = "⚪ غیرفعال"

# --- courses ---
COURSES_TITLE = "📚 مدیریت دوره‌ها"
BTN_NEW_COURSE = "➕ دوره جدید"
ASK_COURSE_CLASS = "نوع کلاس را انتخاب کن:"
ASK_COURSE_SESSIONS = "تعداد کل جلسات را بفرست (عدد):"
ASK_COURSE_TUITION = "مبلغ شهریه به تومان را بفرست (عدد، یا 0):"
ASK_COURSE_GYM_FEE = "مبلغ ورودی باشگاه به تومان را بفرست (عدد، یا 0):"
ASK_COURSE_ALLOWED = "تعداد غیبت مجاز را بفرست (عدد، یا 0):"
ASK_COURSE_START = "تاریخ شروع را به‌صورت شمسی بفرست (نمونه: 1405/04/28):"
COURSE_CREATED = "🟢 دوره ایجاد شد."
BTN_PAUSE_COURSE = "⏸ توقف"
BTN_RESUME_COURSE = "🟢 ازسرگیری"
BTN_FINISH_COURSE = "✅ پایان دوره"
BTN_RENEW_COURSE = "🔄 تمدید دوره"
ASK_RENEW_SESSIONS = "تعداد جلسات دورهٔ جدید را بفرست (عدد):"
RENEWED = "🟢 دوره تمدید شد و اعتبار باقی‌مانده منتقل شد."

# --- attendance ---
ATTEND_TITLE = "✅ ثبت حضور و غیاب"
ATTEND_PICK_COURSE = "دوره را انتخاب کن:"
ASK_ATTEND_DATE = "تاریخ جلسه را به‌صورت شمسی بفرست (نمونه: 1405/04/28):"
ASK_ATTEND_OUTCOME = "وضعیت حضور را انتخاب کن:"
ASK_ATTEND_NOTE = "یادداشت (اختیاری) را بفرست یا «⏭ رد کردن»:"
ATTEND_SAVED = "🟢 حضور و غیاب ثبت شد."
ATTEND_CONFIRM = "ثبت شود؟"

# --- programs ---
PROGRAMS_TITLE = "📄 مدیریت برنامه‌ها"
PROGRAMS_HINT = "روی عنوان بزن تا فعال/غیرفعال شود · ✏️ ویرایش · 🗑 حذف"
BTN_NEW_PLAN_TYPE = "➕ نوع برنامه جدید"
BTN_ASSIGN_PLAN = "📎 ارسال برنامه به شاگرد"
ASK_PLAN_TYPE = "نوع برنامه را انتخاب کن:"
ASK_PLAN_NOTE = "یادداشت مربی (اختیاری) را بفرست یا «⏭ رد کردن»:"
ASK_PLAN_FILE = "فایل برنامه (PDF/عکس) را بفرست، یا «⏭ رد کردن» برای برنامهٔ متنی:"
ASK_PLAN_TYPE_TITLE = "عنوان نوع برنامه را بفرست:"
PLAN_ASSIGNED = "🟢 برنامه برای شاگرد ثبت و ارسال شد."
BTN_RESEND = "🔁 ارسال دوباره"
PLAN_RESENT = "🟢 برنامه دوباره برای شاگرد ارسال شد."

# --- payments ---
PAYMENTS_TITLE = "💳 مدیریت پرداخت‌ها"
BTN_NEW_PAYMENT = "➕ ثبت پرداخت"
ASK_PAYMENT_AMOUNT = "مبلغ پرداخت به تومان را بفرست (برای اصلاح، عدد منفی):"
ASK_PAYMENT_DATE = "تاریخ پرداخت را به‌صورت شمسی بفرست (نمونه: 1405/04/28):"
ASK_PAYMENT_KIND = "بابت چه چیزی؟"
ASK_PAYMENT_NOTE = "یادداشت (اختیاری) را بفرست یا «⏭ رد کردن»:"
PAYMENT_SAVED = "🟢 پرداخت ثبت شد."
KIND_TUITION = "شهریه"
KIND_GYM_FEE = "ورودی باشگاه"
KIND_OTHER = "سایر"
LABEL_TOTAL_DUE = "مجموع بدهی"
LABEL_PAID = "پرداخت‌شده"
LABEL_OUTSTANDING = "باقی‌مانده"

# --- notifications ---
NOTIFY_TITLE = "🔔 اعلان‌ها"
BTN_BROADCAST = "📢 پیام همگانی"
ASK_BROADCAST = "متن پیام همگانی را بفرست (به همهٔ شاگردان فعال ارسال می‌شود):"
BROADCAST_CONFIRM = "این پیام برای {count} شاگرد ارسال شود؟"
BROADCAST_QUEUED = "🟢 پیام برای ارسال ثبت شد ({count} گیرنده)."
BTN_LOW_SESSIONS = "⚠️ یادآوری جلسات کم"
LOW_SESSIONS_DONE = "🟢 یادآوری‌ها برای دوره‌های کم‌جلسه ارسال شد ({count})."

# --- start menu (text + poster) ---
START_TITLE = "🖼 متن و پوستر منوی استارت"
START_HINT = "متن خوش‌آمد یا پوستر منوی استارت را اینجا تنظیم کن:"
BTN_EDIT_START_TEXT = "✏️ ویرایش متن استارت"
BTN_SET_POSTER = "🖼 تنظیم/تغییر پوستر"
BTN_CLEAR_POSTER = "🗑 حذف پوستر"
ASK_START_TEXT = "متن تازهٔ منوی استارت را بفرست:"
ASK_POSTER = "یک عکس بفرست تا پوستر منوی استارت شود:"
START_TEXT_SAVED = "🟢 متن استارت ذخیره شد."
POSTER_SAVED = "🟢 پوستر استارت ثبت شد."
POSTER_CLEARED = "🟢 پوستر استارت حذف شد."
NOT_A_PHOTO = "لطفاً یک «عکس» بفرست (نه فایل یا متن)."

# --- settings ---
SETTINGS_TITLE = "⚙️ تنظیمات"
SETTINGS_HINT = "یک مورد را برای ویرایش انتخاب کن:"
ASK_SETTING_VALUE = "مقدار تازه را بفرست:"
SETTING_SAVED = "🟢 تنظیمات ذخیره شد."
SETTINGS_LABELS = {
    "coach_display_name": "نام مربی",
    "card_number": "شماره کارت",
    "main_intro_message": "پیام خوش‌آمد",
    "registration_contact_message": "متن ثبت‌نام کلاس",
    "plan_order_message": "متن سفارش برنامه",
    "contact_intro_message": "متن راه‌های ارتباطی",
    "signup_url": "لینک سفارش برنامه",
    "default_allowed_absence": "غیبت مجاز پیش‌فرض",
    "low_session_threshold": "آستانه هشدار جلسات کم",
    "telegram_owner_contact": "تماس مربی (تلگرام)",
    "bale_owner_contact": "تماس مربی (بله)",
    "notify_on_attendance": "اعلان خودکار حضور (0/1)",
}
