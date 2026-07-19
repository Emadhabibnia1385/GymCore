"""All user-facing Persian bot strings in one place.

Editable message *content* (intros, contact / registration / plan-order copy)
lives in the database (services.settings) so the coach can reword it without a
code change. This module holds the fixed scaffolding: button labels, navigation
copy, empty states and error fallbacks.
"""

# --- Client main-menu buttons (exact per product spec) ---
BTN_REGISTER_CLASS = "🏋️ ثبت‌نام در کلاس‌ها"
BTN_ORDER_PLAN = "📋 سفارش برنامه"
BTN_MY_CLASSES = "🗓 کلاس‌های من"
BTN_MY_PLANS = "📄 برنامه‌های من"
BTN_CONTACT = "📞 راه‌های ارتباطی ما"
BTN_ADMIN_PANEL = "⚙️ ورود به پنل مدیریت"

# --- Navigation ---
BTN_BACK = "🔙 بازگشت"
BTN_BACK_TO_MENU = "🔙 بازگشت به منوی اصلی"
BTN_HOME = "🏠 منوی اصلی"

# --- Plan order ---
BTN_PLAN_SIGNUP = "🟢 سفارش برنامه از وب‌سایت"

MENU_PROMPT = "از منوی زیر انتخاب کن 👇"
BACK_TO_MENU = "به منوی اصلی بازگشتی 🟢"

TITLE_MY_COURSES = "🗓 کلاس‌های من — یکی را برای جزئیات انتخاب کن:"
TITLE_MY_PROGRAMS = "📄 برنامه‌های من — یکی را برای دریافت انتخاب کن:"
PROGRAM_SENT = "🟢 این هم برنامه‌ات. سلامت باشی!"

NO_COURSES = (
    "هنوز کلاسی به نامت ثبت نشده است.\n"
    "برای شروع، از «🏋️ ثبت‌نام در کلاس‌ها» با من در تماس باش 🌱"
)
NO_PROGRAMS = "هنوز برنامه‌ای برایت ثبت نشده است. به‌زودی مسیرت را با هم می‌چینیم 🟢"
NO_CONTACT_LINKS = "هنوز راه ارتباطی‌ای تنظیم نشده است."

UNKNOWN = "متوجه نشدم 🌿 لطفاً از دکمه‌های منو استفاده کن."
ERROR = "چیزی درست پیش نرفت. کمی بعد دوباره تلاش کن."
ACCESS_DENIED = "این بخش مخصوص مدیر است."
NOT_FOUND = "موردی پیدا نشد."

# --- Course detail (client view) ---
LABEL_STATUS = "وضعیت"
LABEL_START = "تاریخ شروع"
LABEL_TOTAL = "کل جلسات"
LABEL_CONSUMED = "جلسات استفاده‌شده"
LABEL_REMAINING = "جلسات باقی‌مانده"
LABEL_ALLOWED_ABSENCE = "غیبت مجاز"
LABEL_ATTENDANCE_HISTORY = "تاریخچه حضور"
LABEL_FINANCIAL = "خلاصه مالی"
LABEL_TUITION = "شهریه"
LABEL_GYM_FEE = "ورودی باشگاه"
LABEL_PAID = "پرداخت‌شده"
LABEL_OUTSTANDING = "باقی‌مانده"
NO_ATTENDANCE_YET = "هنوز جلسه‌ای ثبت نشده است."
TOMAN = "تومان"

COURSE_STATUS_LABELS = {
    "ACTIVE": "🟢 فعال",
    "FINISHED": "✅ پایان‌یافته",
    "PAUSED": "⏸ متوقف",
}

# --- Admin panel main menu (per product spec) ---
ADMIN_TITLE = "⚙️ پنل مدیریت"
ADMIN_WELCOME = "به پنل مدیریت خوش آمدی 🟢\nیکی از بخش‌ها را انتخاب کن:"
BTN_ADMIN_STUDENTS = "👥 مدیریت شاگردان"
BTN_ADMIN_CLASSES = "🏋️ مدیریت کلاس‌ها"
BTN_ADMIN_COURSES = "📚 مدیریت دوره‌ها"
BTN_ADMIN_ATTENDANCE = "✅ ثبت حضور و غیاب"
BTN_ADMIN_PLANS = "📄 مدیریت برنامه‌ها"
BTN_ADMIN_PAYMENTS = "💳 مدیریت پرداخت‌ها"
BTN_ADMIN_NOTIFY = "🔔 اعلان‌ها"
BTN_ADMIN_SETTINGS = "⚙️ تنظیمات"
BTN_ADMIN_EXIT = "🏠 خروج از پنل مدیریت"
