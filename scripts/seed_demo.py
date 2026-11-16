"""Fill a throwaway local database with a realistic gym, for the web panel.

Usage: python scripts/seed_demo.py <path/to/demo.db>   (never point it at a real database)
"""
import itertools
import os
import sys
from datetime import timedelta

os.environ.update({
    "DATABASE_URL": f"sqlite:///{sys.argv[1]}",
    "TELEGRAM_OWNER_IDS": "111", "TELEGRAM_BOT_TOKEN": "",
})
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app.models  # noqa: F401
from app.core import clock
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import AttendanceStatus as S
from app.models import ExpenseCategory, LeadSource, PaymentKind, Platform
from app.services import (
    attendance,
    auth,
    bootstrap,
    classes,
    courses,
    crm,
    finance,
    identities,
    notifications,
    payments,
    persons,
    schedule,
)

notifications.enabled = False
Base.metadata.create_all(bind=engine)
db = SessionLocal()
bootstrap.seed_all(db)
today = clock.today()
fit = classes.create(db, title="فیتنس")
trx = classes.create(db, title="تی‌آر‌ایکس")
names = ["سارا احمدی", "مریم کریمی", "نگار رضایی", "زهرا محمدی", "علی رستمی", "رضا کاظمی"]
for i, name in enumerate(names):
    p = persons.create(db, name=name, phone=f"0912{i}000000")
    c = courses.create(
        db, client_id=p.id, class_type_id=(fit if i % 2 == 0 else trx).id, sessions_total=12,
        tuition=1_200_000 + i * 100_000, allowed_absence=2,
        start_date=today - timedelta(days=15 + i * 9), weekdays="0,2,4" if i % 2 == 0 else "1,3,5",
        class_times="0@18:00,2@18:00,4@18:00" if i % 2 == 0 else "1@19:30,3@19:30,5@19:30",
    )
    days = schedule.parse_weekdays(c.weekdays)
    # A few sessions already held; the rest stay ahead, so the course is still running.
    for d in itertools.islice(itertools.takewhile(lambda d: d <= today, schedule.iter_scheduled(c.start_date, days)), 4):
        attendance.record(db, c.id, d, S.PRESENT, notify=False)
    paid = [1_200_000, 600_000, 1_500_000, 0, 700_000, 1_000_000][i]
    if paid:
        payments.record(db, p.id, paid, PaymentKind.TUITION, c.start_date, course_id=c.id, notify=False)
# income and costs across the year, so the chart has a shape
import random

random.seed(3)
for back in range(0, 330, 11):
    day = today - timedelta(days=back)
    payments.record(db, 1, random.randrange(300, 1500) * 1000, PaymentKind.TUITION, day, notify=False)
    if back % 22 == 0:
        finance.record_expense(db, random.randrange(200, 900) * 1000, random.choice(list(ExpenseCategory)), day)
finance.record_expense(db, 15_000_000, ExpenseCategory.RENT, today - timedelta(days=2), note="اجاره")
crm.create_lead(db, "مینا صادقی", source=LeadSource.INSTAGRAM)
owner = identities.get_or_create_person(db, Platform.TELEGRAM, "111", "مهدی سرمد")
auth.sync_owner_role(db, Platform.TELEGRAM, "111", owner)
student = persons.get(db, 1)
identities.link_identity(db, student.id, Platform.TELEGRAM, "5001")
print("demo data ready:", sys.argv[1])
