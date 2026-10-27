"""Admin screens that used to strand or mislead the coach (found by walking
every screen): the empty payments page, one-tap deletes, an unclearable phone,
and finished courses listed as «no course»."""

from datetime import date

from app.copy import admin_texts as A
from app.models import AttendanceStatus, PaymentKind
from app.services import attendance as attendance_service
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import payments as payments_service
from app.services import persons as persons_service
from tests.fakes import button_texts, callback_update, last_markup, last_text, make_dispatcher

OWNER = 111
CHAT = 900
START = date(2026, 7, 25)


def _course(db, name, tuition, sessions_total=12):
    client = persons_service.create(db, name=name)
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db, client_id=client.id, class_type_id=class_type.id, sessions_total=sessions_total,
        tuition=tuition, start_date=START, weekdays="0,2,4",
    )
    return client, course


def test_payments_front_page_lists_who_still_owes(db):
    sara, small = _course(db, "سارا", tuition=500_000)
    maryam, big = _course(db, "مریم", tuition=2_000_000)
    zahra, settled = _course(db, "زهرا", tuition=300_000)
    payments_service.record(db, zahra.id, 300_000, PaymentKind.TUITION, START,
                            course_id=settled.id, notify=False)
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, "a:pay"))
    labels = button_texts(last_markup(client))
    assert labels[0].startswith("مریم") and labels[1].startswith("سارا")  # largest first
    assert not any(label.startswith("زهرا") for label in labels)  # settled: not listed
    assert "2 دوره هنوز بدهی دارد" in last_text(client)


def test_payments_front_page_when_everyone_has_paid(db):
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, "a:pay"))
    assert A.PAYMENTS_ALL_SETTLED in last_text(client)


def test_a_debt_is_never_shown_green(db):
    sara, course = _course(db, "سارا", tuition=500_000)
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:pay:course:{course.id}"))
    assert "🔴 500,000" in last_text(client) and "👤 سارا" in last_text(client)
    disp.handle_update(callback_update(2, CHAT, OWNER, f"a:pay:client:{sara.id}"))
    assert last_text(client).startswith(A.PAYMENTS_OF.format(name="سارا"))


def test_deleting_a_class_asks_first(db):
    spare = classes_service.create(db, title="کلاس اضافه")
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:classes:del_confirm:{spare.id}"))
    assert A.BTN_YES_DELETE in button_texts(last_markup(client))
    assert classes_service.get(db, spare.id) is not None  # nothing deleted yet
    disp.handle_update(callback_update(2, CHAT, OWNER, f"a:classes:delete:{spare.id}"))
    assert last_text(client).startswith(A.CLASS_DELETED)


def test_a_refused_class_delete_is_one_screen(db):
    _, course = _course(db, "سارا", tuition=0)
    disp, client = make_dispatcher()
    before = len(client.sent)
    disp.handle_update(
        callback_update(1, CHAT, OWNER, f"a:classes:delete:{course.class_type_id}")
    )
    assert len(client.sent) == before + 1 and last_text(client).startswith("⚠️")


def test_a_phone_is_removed_with_a_tap(db):
    person = persons_service.create(db, name="سارا", phone="09121111111")
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:students:edit_phone:{person.id}"))
    assert A.BTN_CLEAR_PHONE in button_texts(last_markup(client))
    disp.handle_update(
        callback_update(2, CHAT, OWNER, f"a:students:clear:edit_phone:{person.id}")
    )
    db.expire_all()
    assert persons_service.get(db, person.id).phone is None


def test_a_finished_course_is_not_no_course(db):
    """«🏁 دوره تمام شده» sits above «بدون دوره»: they're the ones to call."""
    persons_service.create(db, name="بی‌دوره")
    done, course = _course(db, "تمام‌کرده", tuition=0, sessions_total=1)
    attendance_service.record(db, course.id, START, AttendanceStatus.PRESENT, notify=False)
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, "a:students"))
    labels = button_texts(last_markup(client))
    ended, empty = labels.index(A.COURSE_ENDED), labels.index(A.NO_COURSE)
    assert ended < empty


def test_messaging_a_student_without_the_bot_is_one_screen(db):
    person = persons_service.create(db, name="سارا")
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:students:msg:{person.id}"))
    assert len(client.sent) == 1
    assert last_text(client).startswith(A.STUDENT_NO_ACCOUNT)
