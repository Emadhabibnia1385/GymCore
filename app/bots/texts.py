"""All Persian bot strings in one place (UI language: Persian, code: English).

Tone: warm, encouraging, lightly literary — GymCore speaks to the athlete
like a companion on the road, not a form. Button labels stay short and
iconic on purpose (they are also the router keys in handlers.py); the
literary voice lives in the prose below.
"""

# Main menu buttons — exactly as specified in the product spec.
BTN_REGISTER_CLASS = "🏋️ ثبت‌نام کلاس"
BTN_ORDER_PLAN = "📋 سفارش برنامه"
BTN_MY_CLASSES = "🗓 کلاس‌های من"
BTN_MY_PLANS = "📄 برنامه‌های من"
BTN_CONTACT = "📞 راه‌های ارتباطی ما"

BTN_BACK = "🔙 بازگشت"
BTN_SHARE_PHONE = "📱 ارسال شماره من"

# Inline button that opens the plan-order signup (Telegram Mini App / Bale link).
BTN_PLAN_SIGNUP = "📝 تکمیل فرم سفارش برنامه"

ASK_NAME = "سفرِ تو از همین‌جا آغاز می‌شود 🌱\nبرای شروع، نام و نام خانوادگی‌ات را برایم بنویس."
ASK_PHONE = (
    "بسیار خوب! حالا شماره‌ی همراهت را برایم بفرست تا در را به رویت بگشاییم.\n"
    "می‌توانی دکمه‌ی «📱 ارسال شماره من» را بزنی یا شماره را خودت تایپ کنی."
)
INVALID_PHONE = "این شماره چندان درست به نظر نمی‌رسد 🤔\nلطفاً به شکل 09xxxxxxxxx واردش کن."
REGISTERED = (
    "به جمع ما خوش آمدی 🌿\n"
    "از این لحظه هم‌قدمِ تو در مسیر تناسب‌اندام هستیم. از منوی زیر آغاز کن:"
)

MENU = "چه کمکی از دستم برمی‌آید؟"
BACK_TO_MENU = "به منوی اصلی بازگشتی 🌿"

# «ثبت‌نام کلاس» → راه‌های ارتباطی (به‌جای درخواست درون‌رباتی)
CLASS_CONTACT_INTRO = (
    "برای ثبت‌نام در کلاس، از یکی از راه‌های ارتباطی زیر به من پیام بده\n"
    "تا کلاسِ موردنظرت را با هم هماهنگ و نهایی کنیم 🌿"
)

# «سفارش برنامه» → فرم ثبت‌نام (Mini App تلگرام / لینک بله)
PLAN_SIGNUP_INTRO = (
    "برای سفارش برنامه‌ی اختصاصی، فرم زیر را باز و تکمیل کن 🌿\n"
    "پس از ثبت، برنامه‌ات آماده و برایت ارسال می‌شود."
)

NO_COURSES = "هنوز دوره‌ای به نامت ثبت نشده است؛ نخستین قدم را همین امروز بردار 🌱"
NO_PLANS = "هنوز برنامه‌ای برایت آماده نشده است؛ به‌زودی مسیرت را با هم ترسیم می‌کنیم."

UNKNOWN = "متوجه منظورت نشدم 🌿 لطفاً از دکمه‌های منو کمک بگیر."
ERROR = "چیزی آن‌طور که باید پیش نرفت. لحظه‌ای دیگر دوباره تلاش کن."
