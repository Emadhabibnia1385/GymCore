"""Persian copy for the in-bot finance screens: the monthly report, the year
summary, and recording the gym's expenses.

Generic scaffolding («🔙 بازگشت», «✖️ لغو», «⏭ رد کردن», «تاریخ نامعتبر…») and
the payment-kind labels are reused from admin_texts; everything new lives here.
"""

# --- entry points (on the payments front page) ---
BTN_MONTH_REPORT = "📊 گزارش ماه"
BTN_NEW_EXPENSE = "➖ ثبت هزینه"

# --- expense categories, keyed by ExpenseCategory name ---
CATEGORY_LABELS = {
    "RENT": "اجاره",
    "EQUIPMENT": "تجهیزات",
    "SALARY": "حقوق",
    "ADS": "تبلیغات",
    "BILLS": "قبوض",
    "OTHER": "سایر",
}

# --- month report ---
REPORT_TITLE = "📊 گزارش مالی — {month} {year}"
LABEL_INCOME = "💰 درآمد"
LABEL_EXPENSES = "💸 هزینه"
LABEL_NET = "سود خالص"
LABEL_PAYMENT_COUNT = "🔢 تعداد پرداخت‌ها"
PAYMENT_CORRECTIONS = "(و {n} اصلاحیه)"
BREAKDOWN_ROW = "• {label}: {amount}"
BTN_PREV_MONTH = "◀️ ماه قبل"
BTN_NEXT_MONTH = "ماه بعد ▶️"
BTN_YEAR_SUMMARY = "📅 خلاصهٔ سال"
BTN_MONTH_EXPENSES = "🧾 هزینه‌های این ماه"

# --- year summary ---
YEAR_TITLE = "📅 خلاصهٔ سال {year}"
YEAR_HINT = "درآمد / هزینه / سود خالص — به تومان"
YEAR_ROW = "{month}: {income} / {expenses} / {net}"
YEAR_ROW_EMPTY = "{month}: —"
YEAR_TOTAL = "جمع سال: {income} / {expenses} / {net}"
YEAR_PICK_MONTH = "روی هر ماه بزن تا گزارشش باز شود 👇"

# --- the expenses of one month ---
EXPENSES_TITLE = "🧾 هزینه‌های {month} {year}"
EXPENSES_EMPTY = "هنوز هزینه‌ای برای این ماه ثبت نشده است."
EXPENSE_ROW = "• {date} · {category} · {amount}"
EXPENSES_TOTAL = "جمع: {amount} ({n} مورد)"

# --- recording an expense ---
ASK_AMOUNT = "مبلغ هزینه به تومان را بفرست (برای اصلاح یک هزینهٔ اشتباه، عدد منفی):"
ASK_CATEGORY = "💸 {amount}\nبابت چه؟ دسته‌اش را انتخاب کن 👇"
ASK_DATE = "تاریخ هزینه را به‌صورت شمسی بفرست (نمونه: 1405/04/28)، یا «📅 امروز» را بزن:"
BTN_TODAY = "📅 امروز — {date}"
ASK_NOTE = "یادداشت (اختیاری) را بفرست — مثلاً «اجارهٔ مهر» — یا «⏭ رد کردن» را بزن:"
NOTE_NEEDS_TEXT = "⚠️ یادداشت فقط متن است؛ بنویسش یا «⏭ رد کردن» را بزن."
EXPENSE_SAVED = "🟢 هزینه ثبت شد: {category} · {amount}"
CORRECTION_SAVED = "🟢 اصلاحیه ثبت شد: {category} · {amount}"
STEP_EXPIRED = "⌛ این مرحله دیگر فعال نیست؛ از «➖ ثبت هزینه» دوباره شروع کن 👇"

# --- validation (raised by services/finance.py) ---
AMOUNT_ZERO = "⚠️ مبلغ هزینه نمی‌تواند صفر باشد."
AMOUNT_TOO_LARGE = "⚠️ این مبلغ بیش از حد بزرگ است؛ دوباره نگاهش کن."
DATE_IN_FUTURE = "⚠️ تاریخ هزینه نمی‌تواند در آینده باشد."
DATE_TOO_OLD = "⚠️ تاریخ هزینه باید در یک سال گذشته باشد — سالش را درست نوشتی؟"
