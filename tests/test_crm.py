"""«📇 پیگیری‌ها»: who should renew, leads, a student's notes and follow-ups —
the services, the admin screens driven through the dispatcher, and the coach's
morning digest."""

from datetime import date, datetime, time, timedelta

import pytest
from sqlalchemy import func, select

from app.bots.common import callbacks as cb
from app.copy import admin_texts as A
from app.copy import crm_texts as C
from app.copy import texts
from app.core.jalali import format_jalali
from app.models import (
    AttendanceStatus,
    CourseStatus,
    FollowUp,
    Lead,
    LeadSource,
    LeadStatus,
    Notification,
    NotificationStatus,
    Person,
    PersonNote,
    Platform,
    Role,
    StudentType,
)
from app.notifications import digest, worker
from app.notifications import service as notify_service
from app.services import attendance as attendance_service
from app.services import auth
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import crm as crm_service
from app.services import identities as identities_service
from app.services import persons as persons_service
from tests.fakes import (
    button_texts,
    callback_update,
    last_markup,
    last_text,
    make_dispatcher,
    message_update,
    register,
)

OWNER = 111
CHAT = 900


def _today() -> date:
    return crm_service.local_today()


def _days_ago(n: int) -> date:
    return _today() - timedelta(days=n)


def _course(db, name, sessions_total=1, phone=None, start=None):
    student = persons_service.create(db, name=name, phone=phone)
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db, client_id=student.id, class_type_id=class_type.id, sessions_total=sessions_total,
        start_date=start or _days_ago(30), weekdays="0,2,4",
    )
    return student, course


def _attend(db, course, day, status=AttendanceStatus.PRESENT):
    return attendance_service.record(db, course.id, day, status, notify=False)


def _finished(db, name, ended_on, phone=None):
    """A student whose one-session course ended on `ended_on`."""
    student, course = _course(db, name, phone=phone, start=ended_on)
    _attend(db, course, ended_on)  # the last paid session: the course auto-finishes
    return student, course


def _callbacks(markup) -> list[str]:
    return [b["callback_data"] for row in markup["inline_keyboard"] for b in row
            if "callback_data" in b]


def _tap(disp, client, label, update_id=50):
    """Tap the on-screen button whose text is (or starts with) `label`."""
    for row in last_markup(client)["inline_keyboard"]:
        for button in row:
            if button["text"] == label or button["text"].startswith(label):
                disp.handle_update(callback_update(update_id, CHAT, OWNER, button["callback_data"]))
                return
    raise AssertionError(f"no {label!r} among {button_texts(last_markup(client))}")


def _all_callback_data(client):
    for sent in client.sent:
        for row in (sent.get("reply_markup") or {}).get("inline_keyboard", []):
            for button in row:
                if "callback_data" in button:
                    yield button["callback_data"]


# --- renewal candidates ---


def test_only_a_finished_latest_course_with_nothing_active_is_a_renewal(db):
    _finished(db, "تمام‌کرده", _days_ago(5))
    _, running = _course(db, "فعال", sessions_total=4)
    _attend(db, running, _days_ago(5))
    persons_service.create(db, name="بی‌دوره")
    # A new course after the finished one: not waiting to renew.
    moved_on, old = _finished(db, "دوره تازه", _days_ago(9))
    courses_service.create(db, client_id=moved_on.id, class_type_id=old.class_type_id,
                           sessions_total=8, start_date=_today())
    # The latest course finished but an older one still runs: not a renewal either.
    odd, older = _course(db, "دو دوره", sessions_total=8)
    newer = courses_service.create(db, client_id=odd.id, class_type_id=older.class_type_id,
                                   sessions_total=1, start_date=_days_ago(3))
    _attend(db, newer, _days_ago(3))

    names = [c.person.name for c in crm_service.renewal_candidates(db)]
    assert names == ["تمام‌کرده"]


def test_the_end_date_is_the_last_session_that_happened(db):
    student, course = _course(db, "سارا", sessions_total=3, start=_days_ago(20))
    first, last = _days_ago(20), _days_ago(16)
    _attend(db, course, first)
    _attend(db, course, last, AttendanceStatus.ABSENT_UNAUTHORIZED)
    # A correction recorded afterwards on the earlier date doesn't move the end…
    attendance_service.correct(db, course.id, first, AttendanceStatus.ABSENT_UNAUTHORIZED)
    # …and a later session moved away vacated its date: it never happened.
    attendance_service.move_session(db, course.id, _days_ago(14), _days_ago(13), notify=False)
    courses_service.set_status(db, course.id, CourseStatus.FINISHED)  # finished by hand

    (candidate,) = crm_service.renewal_candidates(db)
    assert (candidate.person.id, candidate.course.id) == (student.id, course.id)
    assert candidate.ended_on == last
    assert candidate.days_since == 16


def test_a_renewed_student_drops_out(db):
    student, course = _finished(db, "مریم", _days_ago(2))
    assert [c.person.id for c in crm_service.renewal_candidates(db)] == [student.id]
    courses_service.renew(db, course.id, sessions_total=12)
    assert crm_service.renewal_candidates(db) == []


def test_most_recent_first_and_whether_anyone_followed_up_since(db):
    early, _ = _finished(db, "زودتر", _days_ago(10))
    late, _ = _finished(db, "دیرتر", _days_ago(2))
    # A note written before the course ended is not following up on it.
    note = crm_service.add_note(db, late.id, "قبل از پایان دوره")
    note.created_at = datetime.combine(_days_ago(8), time(9, 0))  # stored as UTC
    db.commit()
    crm_service.add_follow_up(db, _today() + timedelta(days=2), person_id=early.id)

    candidates = crm_service.renewal_candidates(db)
    assert [c.person.name for c in candidates] == ["دیرتر", "زودتر"]
    assert [c.followed_up for c in candidates] == [False, True]
    assert [c.days_since for c in candidates] == [2, 10]


def test_summary_waits_only_on_what_needs_the_coach(db):
    assert not crm_service.summary(db).waiting
    student, _ = _finished(db, "مریم", _days_ago(1))
    assert crm_service.summary(db).waiting  # a course ended, nobody has called
    crm_service.add_note(db, student.id, "زنگ زدم")
    assert not crm_service.summary(db).waiting
    lead = crm_service.create_lead(db, name="نیما")
    assert crm_service.summary(db).waiting  # a new lead, nothing planned
    crm_service.set_lead_follow_up(db, lead.id, _today() + timedelta(days=3))
    summary = crm_service.summary(db)
    assert (summary.due, summary.renewals, summary.leads, summary.waiting) == (0, 1, 1, False)
    assert crm_service.summary(db, _today() + timedelta(days=3)).waiting  # …until it is due


# --- the renewal screens ---


def test_renewal_screen_offers_profile_note_follow_up_and_renew(db):
    student, course = _finished(db, "مریم", _days_ago(4), phone="09123334455")
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, "a:crm"))
    assert C.BTN_RENEWALS.format(n=1) in button_texts(last_markup(client))
    disp.handle_update(callback_update(2, CHAT, OWNER, "a:crm:ren"))
    labels = button_texts(last_markup(client))
    assert "مریم" in labels
    assert f"{C.RENEWAL_WAITING} {C.DAYS_AGO.format(n=4)}" in labels

    disp.handle_update(callback_update(3, CHAT, OWNER, f"a:crm:rc:{student.id}"))
    body, calls = last_text(client), _callbacks(last_markup(client))
    assert C.CANDIDATE_TITLE.format(name="مریم") in body and "09123334455" in body
    assert C.CANDIDATE_WAITING in body
    for expected in (
        f"a:students:view:{student.id}",
        f"a:courses:renew:{course.id}",  # the existing confirm screen
        f"a:crm:notes:{student.id}:r",
        f"a:crm:pfu:{student.id}:r",
    ):
        assert expected in calls
    disp.handle_update(callback_update(4, CHAT, OWNER, f"a:courses:renew:{course.id}"))
    assert A.BTN_YES_RENEW in button_texts(last_markup(client))

    # A note from here: saved on the timeline, which leads back to the renewal.
    disp.handle_update(callback_update(5, CHAT, OWNER, f"a:crm:notes:{student.id}:r"))
    disp.handle_update(message_update(6, CHAT, OWNER, "زنگ زدم؛ هفتهٔ بعد تمدید می‌کند"))
    assert last_text(client).startswith(C.NOTE_SAVED)
    assert f"a:crm:rc:{student.id}" in _callbacks(last_markup(client))
    disp.handle_update(callback_update(7, CHAT, OWNER, f"a:crm:rc:{student.id}"))
    assert C.CANDIDATE_FOLLOWED in last_text(client)

    # Renewed: a stale renewal screen says so instead of offering it again.
    disp.handle_update(callback_update(8, CHAT, OWNER, f"a:courses:renew_go:{course.id}"))
    disp.handle_update(callback_update(9, CHAT, OWNER, f"a:crm:rc:{student.id}"))
    assert last_text(client).startswith(C.NOT_A_CANDIDATE.format(name="مریم"))


# --- leads ---


def test_a_lead_from_first_question_to_student(db):
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, "a:crm"))
    _tap(disp, client, C.BTN_NEW_LEAD, 2)
    disp.handle_update(message_update(3, CHAT, OWNER, "نگار احمدی"))
    disp.handle_update(message_update(4, CHAT, OWNER, "123"))
    assert C.ERR_PHONE_INVALID in last_text(client)  # asked again, still in the flow
    disp.handle_update(message_update(5, CHAT, OWNER, "۰۹۱۲۳۴۵۶۷۸۹"))  # Persian digits
    _tap(disp, client, C.SOURCE_LABELS["INSTAGRAM"], 6)
    disp.handle_update(message_update(7, CHAT, OWNER, "کلاس فیتنس"))
    db.expire_all()
    lead = db.scalar(select(Lead))
    assert (lead.name, lead.phone, lead.source, lead.interest, lead.status) == (
        "نگار احمدی", "09123456789", LeadSource.INSTAGRAM, "کلاس فیتنس", LeadStatus.NEW,
    )
    assert lead.created_by == str(OWNER)
    assert last_text(client).startswith(C.LEAD_SAVED)
    assert C.LEAD_TITLE.format(name="نگار احمدی") in last_text(client)

    _tap(disp, client, C.STATUS_LABELS["CONTACTED"], 8)
    assert last_text(client).startswith(C.STATUS_SAVED.format(status=C.STATUS_LABELS["CONTACTED"]))
    _tap(disp, client, C.BTN_LEAD_NOTE, 9)
    disp.handle_update(message_update(10, CHAT, OWNER, "گفت هفتهٔ بعد می‌آید"))
    _tap(disp, client, f"⏰ {C.SHORTCUT_LABELS[3]}", 11)
    db.expire_all()
    lead = crm_service.get_lead(db, lead.id)
    in_three = _today() + timedelta(days=3)
    assert lead.status == LeadStatus.CONTACTED and lead.next_follow_up == in_three
    assert "گفت هفتهٔ بعد می‌آید" in lead.note
    assert crm_service.list_due(db) == []
    (due,) = crm_service.list_due(db, in_three)
    assert due.lead_id == lead.id

    _tap(disp, client, C.BTN_CONVERT, 12)
    assert last_text(client) == C.CONFIRM_CONVERT.format(name="نگار احمدی")
    _tap(disp, client, A.TYPE_LABELS["IN_PERSON"], 13)
    db.expire_all()
    lead = crm_service.get_lead(db, lead.id)
    student = persons_service.get(db, lead.person_id)
    assert lead.status == LeadStatus.WON and lead.next_follow_up is None
    assert (student.name, student.phone, student.role, student.student_type) == (
        "نگار احمدی", "09123456789", Role.CLIENT, StudentType.IN_PERSON,
    )
    # The new student's profile opens, with the result on top.
    assert last_text(client).startswith(C.CONVERTED.format(name="نگار احمدی"))
    assert "👤 نگار احمدی" in last_text(client)
    # The follow-up moved with them; how they came in opens their timeline.
    (moved,) = crm_service.open_follow_ups(db, student.id)
    assert moved.id == due.id and moved.lead_id is None
    (note,) = crm_service.list_notes(db, student.id)
    for part in (C.SOURCE_LABELS["INSTAGRAM"], "کلاس فیتنس", "گفت هفتهٔ بعد می‌آید"):
        assert part in note.text
    assert max(len(data.encode()) for data in _all_callback_data(client)) <= 64


def test_converting_a_lead_whose_phone_is_a_student_links_them(db):
    existing = persons_service.create(db, name="سارا قدیمی", phone="09121111111")
    lead = crm_service.create_lead(db, name="سارا", phone="0912 111 1111",
                                   source=LeadSource.REFERRAL)
    assert lead.phone == "09121111111"  # normalized

    def clients():
        return db.scalar(select(func.count()).select_from(Person)
                         .where(Person.role == Role.CLIENT))

    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:crm:lead:{lead.id}"))
    assert C.LEAD_PHONE_KNOWN.format(name="سارا قدیمی") in last_text(client)
    disp.handle_update(callback_update(2, CHAT, OWNER, f"a:crm:cgo:{lead.id}:I"))
    db.expire_all()
    assert clients() == 1
    assert crm_service.get_lead(db, lead.id).person_id == existing.id
    assert last_text(client).startswith(C.CONVERT_LINKED.format(name="سارا قدیمی"))
    # A second tap from an old screen creates nothing.
    disp.handle_update(callback_update(3, CHAT, OWNER, f"a:crm:cgo:{lead.id}:O"))
    db.expire_all()
    assert clients() == 1
    assert persons_service.get(db, existing.id).student_type == StudentType.IN_PERSON


def test_leads_are_listed_by_status(db):
    crm_service.create_lead(db, name="آرش")
    contacted = crm_service.create_lead(db, name="بهار")
    crm_service.set_lead_status(db, contacted.id, LeadStatus.CONTACTED)
    lost = crm_service.create_lead(db, name="کاوه")
    crm_service.set_lead_status(db, lost.id, LeadStatus.LOST)
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, "a:crm"))
    assert C.BTN_LEADS.format(n=2) in button_texts(last_markup(client))  # open ones only
    disp.handle_update(callback_update(2, CHAT, OWNER, "a:crm:leads"))
    labels = button_texts(last_markup(client))
    assert A.TAB_SELECTED.format(label=f"{C.STATUS_LABELS['NEW']} (1)") in labels
    assert f"{C.STATUS_LABELS['CONTACTED']} (1)" in labels
    assert f"{C.STATUS_LABELS['LOST']} (1)" in labels
    assert "آرش" in labels and "بهار" not in labels
    disp.handle_update(callback_update(3, CHAT, OWNER, "a:crm:leads:C"))
    labels = button_texts(last_markup(client))
    assert "بهار" in labels and "آرش" not in labels


def test_a_lost_lead_stops_being_chased_and_deleting_asks_first(db):
    lead = crm_service.create_lead(db, name="نیما", phone="09351234567")
    lead_id = lead.id
    in_three = _today() + timedelta(days=3)
    crm_service.set_lead_follow_up(db, lead.id, in_three)
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:crm:lead:{lead.id}"))
    _tap(disp, client, C.BTN_LOST, 2)
    assert last_text(client).startswith(C.LEAD_LOST.format(name="نیما"))
    db.expire_all()
    lead = crm_service.get_lead(db, lead.id)
    assert lead.status == LeadStatus.LOST and lead.next_follow_up is None
    assert crm_service.list_due(db, in_three) == []
    _tap(disp, client, C.STATUS_LABELS["CONTACTED"], 3)  # reopened with a tap
    db.expire_all()
    assert crm_service.get_lead(db, lead.id).status == LeadStatus.CONTACTED

    _tap(disp, client, C.BTN_LEAD_PHONE, 4)  # the phone: replaced, then removed
    disp.handle_update(message_update(5, CHAT, OWNER, "09357654321"))
    assert last_text(client).startswith(C.PHONE_SAVED)
    _tap(disp, client, C.BTN_LEAD_PHONE, 6)
    _tap(disp, client, C.BTN_CLEAR_PHONE, 7)
    db.expire_all()
    assert crm_service.get_lead(db, lead.id).phone is None

    _tap(disp, client, C.BTN_DELETE_LEAD, 8)
    assert A.BTN_YES_DELETE in button_texts(last_markup(client))
    db.expire_all()
    assert db.get(Lead, lead.id) is not None  # nothing deleted yet
    _tap(disp, client, A.BTN_YES_DELETE, 9)
    assert last_text(client).startswith(C.LEAD_DELETED.format(name="نیما"))
    db.expire_all()
    assert db.get(Lead, lead_id) is None
    assert db.scalar(select(func.count()).select_from(FollowUp)) == 0


# --- follow-ups ---


def test_follow_ups_due_overdue_done_and_postponed(db):
    sara = persons_service.create(db, name="سارا")
    lead = crm_service.create_lead(db, name="نیما")
    today, week_ago = _today(), _days_ago(7)
    overdue = crm_service.add_follow_up(db, _days_ago(2), person_id=sara.id, note="تمدید",
                                        today=week_ago)
    due = crm_service.add_follow_up(db, today, lead_id=lead.id, today=week_ago)
    crm_service.add_follow_up(db, today + timedelta(days=1), person_id=sara.id)
    assert [f.id for f in crm_service.list_due(db)] == [overdue.id, due.id]  # most overdue first
    assert crm_service.count_due(db) == 2
    assert crm_service.get_lead(db, lead.id).next_follow_up == today

    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, "a:crm"))
    assert C.BTN_TODAY.format(n=2) in button_texts(last_markup(client))
    disp.handle_update(callback_update(2, CHAT, OWNER, "a:crm:today"))
    labels = button_texts(last_markup(client))
    assert labels[0].startswith("👤 سارا") and C.WHEN_OVERDUE.format(n=2) in labels[0]
    assert labels[1].startswith("🧲 نیما") and C.WHEN_TODAY in labels[1]

    disp.handle_update(callback_update(3, CHAT, OWNER, f"a:crm:fu:{overdue.id}:t"))
    assert C.FU_TITLE.format(name="سارا") in last_text(client) and "تمدید" in last_text(client)
    assert f"a:students:view:{sara.id}" in _callbacks(last_markup(client))
    _tap(disp, client, C.BTN_DONE, 4)
    assert last_text(client).startswith(C.FU_DONE.format(name="سارا"))  # back on the list

    disp.handle_update(callback_update(5, CHAT, OWNER, f"a:crm:fu:{due.id}:t"))
    assert f"a:crm:lead:{lead.id}" in _callbacks(last_markup(client))
    _tap(disp, client, C.SHORTCUT_LABELS[7], 6)  # pushed back a week
    db.expire_all()
    assert crm_service.list_due(db) == []
    assert crm_service.get_follow_up(db, due.id).due_on == today + timedelta(days=7)
    assert crm_service.get_lead(db, lead.id).next_follow_up == today + timedelta(days=7)
    assert last_text(client).startswith(
        C.FU_MOVED.format(name="نیما", date=format_jalali(today + timedelta(days=7)))
    )
    # «فردا» from a stale screen of the done one: refused on its screen, nothing moves.
    disp.handle_update(callback_update(7, CHAT, OWNER, f"a:crm:pp:{overdue.id}:1:t"))
    assert last_text(client).startswith(f"⚠️ {C.ERR_FOLLOW_UP_DONE}")
    db.expire_all()
    assert crm_service.get_follow_up(db, overdue.id).due_on == _days_ago(2)


def test_a_student_follow_up_from_the_profile_with_a_topic(db):
    sara = persons_service.create(db, name="سارا")
    today = _today()
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:students:view:{sara.id}"))
    _tap(disp, client, C.BTN_FOLLOW_UP, 2)
    assert C.PFU_TITLE.format(name="سارا") in last_text(client)
    disp.handle_update(message_update(3, CHAT, OWNER, "تمدید دوره"))  # the topic, staged
    assert C.PFU_STAGED.format(note="تمدید دوره") in last_text(client)
    _tap(disp, client, C.SHORTCUT_LABELS[1], 4)
    db.expire_all()
    (follow_up,) = crm_service.open_follow_ups(db, sara.id)
    tomorrow = today + timedelta(days=1)
    assert (follow_up.due_on, follow_up.note, follow_up.created_by) == (
        tomorrow, "تمدید دوره", str(OWNER),
    )
    assert last_text(client).startswith(C.FU_SAVED.format(date=format_jalali(tomorrow)))

    # A typed date a whole Jalali year off is refused; a good one is saved.
    _tap(disp, client, C.BTN_OTHER_DATE, 5)
    disp.handle_update(message_update(6, CHAT, OWNER, format_jalali(today - timedelta(days=360))))
    assert C.ERR_DUE_RANGE in last_text(client)
    disp.handle_update(message_update(7, CHAT, OWNER, format_jalali(today + timedelta(days=30))))
    db.expire_all()
    assert [f.due_on for f in crm_service.open_follow_ups(db, sara.id)] == [
        tomorrow, today + timedelta(days=30),
    ]
    # The profile names the next one.
    disp.handle_update(callback_update(8, CHAT, OWNER, f"a:students:view:{sara.id}"))
    assert f"{C.LABEL_NEXT_FOLLOW_UP}: {format_jalali(tomorrow)}" in last_text(client)


# --- notes ---


def test_notes_timeline_newest_first_and_typed_on_its_screen(db):
    sara = persons_service.create(db, name="سارا")
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:students:view:{sara.id}"))
    _tap(disp, client, C.BTN_NOTES, 2)
    assert C.NOTES_TITLE.format(name="سارا") in last_text(client)
    assert C.NOTES_EMPTY in last_text(client)
    disp.handle_update(message_update(3, CHAT, OWNER, "زانویش درد می‌کند"))
    assert last_text(client).startswith(C.NOTE_SAVED)
    disp.handle_update(message_update(4, CHAT, OWNER, "گفت ماه بعد ادامه می‌دهد"))
    disp.handle_update(message_update(5, CHAT, OWNER, "/start"))  # a command is not a note
    db.expire_all()
    notes = crm_service.list_notes(db, sara.id)
    assert [n.text for n in notes] == ["گفت ماه بعد ادامه می‌دهد", "زانویش درد می‌کند"]
    assert {n.created_by for n in notes} == {str(OWNER)}

    disp.handle_update(callback_update(6, CHAT, OWNER, f"a:crm:notes:{sara.id}:p"))
    body = last_text(client)
    assert body.index("گفت ماه بعد") < body.index("زانویش")
    assert f"a:students:view:{sara.id}" in _callbacks(last_markup(client))
    disp.handle_update(callback_update(7, CHAT, OWNER, f"a:students:view:{sara.id}"))
    assert C.BTN_NOTES_COUNT.format(n=2) in button_texts(last_markup(client))


def test_a_long_timeline_still_fits_one_message(db):
    sara = persons_service.create(db, name="سارا")
    for i in range(30):
        crm_service.add_note(db, sara.id, f"یادداشت {i} " + "متن " * 60)
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:crm:notes:{sara.id}:p"))
    body = last_text(client)
    assert len(body) < 4096
    assert "یادداشت 29" in body  # the newest is shown
    assert C.NOTES_OLDER.split("{")[0] in body


# --- the student profile ---


def test_profile_renders_with_notes_and_follow_ups_on_both_platforms(db):
    student, course = _course(db, "سارا", sessions_total=6, start=_today())
    for platform, owner in ((Platform.TELEGRAM, OWNER), (Platform.BALE, 333)):
        disp, client = make_dispatcher(platform)
        disp.handle_update(callback_update(1, CHAT, owner, f"a:students:view:{student.id}"))
        body, markup = last_text(client), last_markup(client)
        labels = button_texts(markup)
        assert "👤 سارا" in body and A.BTN_STUDENT_GRID in labels
        assert C.BTN_NOTES in labels and C.BTN_FOLLOW_UP in labels
        if platform == Platform.BALE:
            assert all("style" not in b for row in markup["inline_keyboard"] for b in row)
        disp.handle_update(callback_update(2, CHAT, owner, "a:crm"))
        assert C.TITLE in last_text(client)


def test_deleting_a_student_takes_their_notes_and_follow_ups_and_keeps_the_lead(db):
    lead = crm_service.create_lead(db, name="نگار", phone="09125556677")
    conversion = crm_service.convert_lead(db, lead.id, student_type=StudentType.ONLINE)
    sid = conversion.person.id
    assert conversion.person.student_type == StudentType.ONLINE
    crm_service.add_note(db, sid, "یادداشت")
    crm_service.add_follow_up(db, _today() + timedelta(days=1), person_id=sid)
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:students:del:{sid}"))
    db.expire_all()
    assert db.get(Person, sid) is None
    assert db.scalar(select(func.count()).select_from(PersonNote)) == 0
    assert db.scalar(select(func.count()).select_from(FollowUp)) == 0
    assert crm_service.get_lead(db, lead.id).person_id is None  # how they came in stays
    disp.handle_update(callback_update(2, CHAT, OWNER, f"a:crm:lead:{lead.id}"))
    assert C.LEAD_TITLE.format(name="نگار") in last_text(client)


def test_admin_menu_has_the_follow_ups_next_to_the_timetable(db):
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, cb.ADMIN))
    rows = last_markup(client)["inline_keyboard"]
    (row,) = [r for r in rows if any(b["text"] == texts.BTN_ADMIN_CRM for b in r)]
    assert [b["text"] for b in row] == [texts.BTN_ADMIN_WEEK, texts.BTN_ADMIN_CRM]
    assert row[1]["callback_data"] == "a:crm"


# --- tamper safety ---


def test_tampered_and_stale_callbacks_get_one_screen_never_an_error(db):
    disp, client = make_dispatcher()
    for i, data in enumerate((
        "a:crm:fu:abc", "a:crm:fu:999999:t", "a:crm:done:", "a:crm:pp:1:2:t", "a:crm:pp:x:1",
        "a:crm:rc:-3", "a:crm:notes:999999:p", "a:crm:pfu::", "a:crm:pfa:1:99:p",
        "a:crm:pfd:999999:p", "a:crm:lead:0", "a:crm:st:1:W", "a:crm:st:abc:N",
        "a:crm:cgo:1:Z", "a:crm:cgo:999999:I", "a:crm:src:I", "a:crm:nskp", "a:crm:nski",
        "a:crm:ldelgo:424242", "a:crm:lfa:1:5", "a:crm:leads:ZZ:page:abc",
        "a:crm:today:page:-1", "a:crm:ren:page:999", "a:crm:💥", "a:crm",
    ), start=1):
        before = len(client.sent)
        disp.handle_update(callback_update(i, CHAT, OWNER, data))
        assert len(client.sent) == before + 1, data  # exactly one screen
        assert last_text(client) != texts.ERROR, data
    disp.handle_update(callback_update(90, CHAT, OWNER, "a:crm:src:I"))  # no lead being added
    assert last_text(client) == C.EXPIRED


def test_a_non_owner_never_reaches_the_follow_ups(db):
    crm_service.create_lead(db, name="نیما")
    disp, client = make_dispatcher()
    register(disp, 7001, 5001)
    before = len(client.sent)
    disp.handle_update(callback_update(1, 7001, 5001, "a:crm:leads"))
    assert client.answered[-1]["text"] == texts.ACCESS_DENIED
    assert len(client.sent) == before


# --- the coach's morning digest ---


@pytest.fixture
def sent():
    """Record what the notification worker delivers, offline."""
    calls: list = []

    def _send(platform, chat_id, text):
        calls.append((platform, chat_id, text))
        return True

    original = notify_service.sender
    notify_service.sender = _send
    yield calls
    notify_service.sender = original


def _tehran(day: date, hour: int, minute: int = 0) -> datetime:
    """Naive UTC for a wall-clock time in Tehran (UTC+03:30)."""
    return datetime.combine(day, time(hour, minute)) - timedelta(hours=3, minutes=30)


def _owners_opened_the_bot(db):
    for platform, owner in ((Platform.TELEGRAM, "111"), (Platform.BALE, "333")):
        person = identities_service.get_or_create_person(db, platform, owner, "مهدی سرمد")
        auth.sync_owner_role(db, platform, owner, person)


def test_the_morning_digest_reaches_each_owner_once_a_day(db, sent):
    _owners_opened_the_bot(db)
    crm_service.create_lead(db, name="نیما")  # nobody has contacted them yet
    day = _today()
    assert digest.queue_digest(db, now=_tehran(day, 7, 45)) == 0  # before 08:00
    assert digest.queue_digest(db, now=_tehran(day, 8, 5)) == 2  # one per owner
    assert digest.queue_digest(db, now=_tehran(day, 14, 0)) == 0  # once a day
    notify_service.dispatch_due(db, now=_tehran(day, 8, 6))
    assert sorted((platform, chat) for platform, chat, _ in sent) == [
        (Platform.BALE, "333"), (Platform.TELEGRAM, "111"),
    ]
    assert {body for _, _, body in sent} == {C.DIGEST.format(due=0, renewals=0, leads=1)}
    assert digest.queue_digest(db, now=_tehran(day + timedelta(days=1), 9, 0)) == 2


def test_a_quiet_morning_sends_nothing_all_day(db, sent):
    _owners_opened_the_bot(db)
    day = _today()
    assert digest.queue_digest(db, now=_tehran(day, 8, 30)) == 0  # nothing waiting
    crm_service.create_lead(db, name="نیما")  # the coach adds one at noon
    assert digest.queue_digest(db, now=_tehran(day, 14, 30)) == 0  # the morning decided
    quiet = db.scalar(select(Notification).where(Notification.idempotency_key.like("crm-%")))
    assert quiet.status == NotificationStatus.CANCELLED and quiet.person_id is None
    assert notify_service.dispatch_due(db) == 0 and sent == []
    assert digest.queue_digest(db, now=_tehran(day + timedelta(days=1), 8, 30)) == 2


def test_the_worker_cycle_sends_the_digest(db, sent):
    _owners_opened_the_bot(db)
    _finished(db, "مریم", _days_ago(1))
    queued, delivered = worker.run_once(now=_tehran(_today(), 9, 0))
    assert queued >= 2 and delivered >= 2
    digests = [body for platform, chat, body in sent if chat in ("111", "333")]
    assert digests == [C.DIGEST.format(due=0, renewals=1, leads=0)] * 2
