"""«📦 پکیج‌ها» end to end through the dispatcher: building a package, sending it
to several students (each told once), what each student opens on their own
platform, and the guards — deactivated, foreign or tampered ids, deleting a
package that was sent, deleting a student who has one."""

import re

import pytest
from sqlalchemy import func, select

from app.bots.common import client_flow
from app.bots.common.client import BotApiError
from app.copy import admin_texts as A
from app.copy import packages_texts as P
from app.copy import texts
from app.models import PackageAssignment, Person, Platform, StudentType
from app.services import notifications
from app.services import packages as packages_service
from app.services import persons as persons_service
from app.services import plans as plans_service
from tests.fakes import (
    button_texts,
    callback_update,
    last_markup,
    last_text,
    make_dispatcher,
    message_update,
    register,
)

OWNER = 111  # a Telegram owner (conftest)
BALE_OWNER = 333  # the Bale owner (conftest)
CHAT = 900
FILE_METHODS = ("send_document_id", "send_photo_id", "send_video_id", "send_document_path")

NEGAR = "09125550001"
SARA = "09125550002"
MINA = "09125550003"


@pytest.fixture()
def notified(monkeypatch):
    """Every notify_person call, as (person_id, text)."""
    calls = []
    monkeypatch.setattr(
        notifications, "notify_person", lambda db, person, text: calls.append((person.id, text))
    )
    return calls


def _file_update(update_id, kind, file_id, caption=None, user=OWNER, chat=CHAT):
    message = {"message_id": 10, "chat": {"id": chat}, "from": {"id": user, "first_name": "مربی"}}
    if kind == "document":
        message["document"] = {"file_id": file_id, "file_name": "diet.pdf"}
    elif kind == "video":
        message["video"] = {"file_id": file_id, "file_name": "squat.mp4", "duration": 30}
    else:
        message["photo"] = [{"file_id": f"{file_id}_small"}, {"file_id": file_id}]
    if caption:
        message["caption"] = caption
    return {"update_id": update_id, "message": message}


def _package(db, title="پکیج کاهش وزن ۸ هفته‌ای"):
    """A package made on Telegram: a diet PDF, a training video and a text."""
    package = packages_service.create(db, title=title, description="هشت هفته غذا و تمرین")
    doc = packages_service.add_item(db, package.id, "document", text="برنامه غذایی هفته اول",
                                    file_id="DOC1", platform=Platform.TELEGRAM,
                                    original_filename="diet.pdf")
    video = packages_service.add_item(db, package.id, "video", text="هفته ۱ — اسکات\n۳ ست ۱۲ تکرار",
                                      file_id="VID1", platform=Platform.TELEGRAM,
                                      original_filename="squat.mp4")
    note = packages_service.add_item(db, package.id, "text", text="نکات مهم: روزی ۸ لیوان آب")
    return package, doc, video, note


def _student(db, name, phone, kind=StudentType.ONLINE):
    return persons_service.create(db, name=name, phone=phone, student_type=kind)


def _file_sends(client):
    return [(m["method"], m.get("file_id")) for m in client.sent if m["method"] in FILE_METHODS]


# --- building a package ---


def test_the_programs_hub_leads_to_packages(db):
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, "a:plans"))
    assert P.BTN_PACKAGES in button_texts(last_markup(client))
    disp.handle_update(callback_update(2, CHAT, OWNER, "a:pkg"))
    assert last_text(client).startswith(P.LIST_TITLE)
    assert P.BTN_NEW in button_texts(last_markup(client))


def test_building_a_package_with_a_pdf_a_video_and_text(db):
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, "a:pkg:new"))
    assert last_text(client) == P.ASK_TITLE
    disp.handle_update(message_update(2, CHAT, OWNER, "پکیج کاهش وزن ۸ هفته‌ای"))
    assert last_text(client) == P.ASK_DESCRIPTION
    disp.handle_update(message_update(3, CHAT, OWNER, "هشت هفته غذا و تمرین"))
    assert last_text(client).startswith(P.CREATED)
    (package,) = packages_service.list_packages(db)

    disp.handle_update(callback_update(4, CHAT, OWNER, f"a:pkg:add:{package.id}"))
    assert last_text(client) == P.ASK_ITEM
    # Several in a row (an album arrives as one message each); captions become the text.
    disp.handle_update(_file_update(5, "document", "DOC1", caption="برنامه غذایی هفته اول"))
    disp.handle_update(_file_update(6, "video", "VID1", caption="هفته ۱ — اسکات\n۳ ست ۱۲ تکرار"))
    disp.handle_update(message_update(7, CHAT, OWNER, "نکات مهم: روزی ۸ لیوان آب"))
    assert last_text(client).startswith(P.ITEM_ADDED.format(label="نکات مهم: روزی ۸ لیوان آب", n=3))
    assert P.BTN_DONE_ADDING in button_texts(last_markup(client))

    db.expire_all()
    doc, video, note = packages_service.items(db, package.id)
    assert (doc.kind, doc.telegram_file_id) == ("document", "DOC1")
    assert doc.original_filename == "diet.pdf"
    assert (video.kind, video.telegram_file_id, video.bale_file_id) == ("video", "VID1", None)
    assert video.text == "هفته ۱ — اسکات\n۳ ست ۱۲ تکرار"
    assert (note.kind, note.telegram_file_id) == ("text", None)
    assert note.text == "نکات مهم: روزی ۸ لیوان آب"

    disp.handle_update(callback_update(8, CHAT, OWNER, f"a:pkg:view:{package.id}"))
    screen = last_text(client)
    assert "1. 📎 برنامه غذایی هفته اول — تلگرام ✅ · بله ⚪" in screen
    assert "2. 🎬 هفته ۱ — اسکات — تلگرام ✅ · بله ⚪" in screen
    assert P.MISSING_COPIES.format(n=2, platform="بله") in screen
    labels = button_texts(last_markup(client))
    assert "3. 📝 نکات مهم: روزی ۸ لیوان آب" in labels
    assert P.BTN_SEND in labels and P.BTN_RECIPIENTS.format(n=0) in labels


def test_a_file_at_the_description_step_starts_the_package(db):
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, "a:pkg:new"))
    disp.handle_update(message_update(2, CHAT, OWNER, "پکیج حجم"))
    disp.handle_update(_file_update(3, "document", "DOC9", caption="برنامه غذایی"))
    (package,) = packages_service.list_packages(db)
    assert package.description is None
    (item,) = packages_service.items(db, package.id)
    assert item.telegram_file_id == "DOC9"
    assert last_text(client).startswith(P.ITEM_ADDED.format(label="برنامه غذایی", n=1))


def test_adding_ends_on_a_command_and_stops_at_the_item_limit(db):
    negar = _student(db, "نگار", NEGAR)
    package = packages_service.create(
        db, title="پ" * packages_service.TITLE_LIMIT,
        description="ت" * packages_service.DESCRIPTION_LIMIT,
    )
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:pkg:add:{package.id}"))
    disp.handle_update(message_update(2, CHAT, OWNER, "/start"))  # «✅ تمام» forgotten
    assert packages_service.items(db, package.id) == []
    assert last_text(client).startswith(f"📦 {package.title}")

    for n in range(packages_service.MAX_ITEMS):  # the longest lines: a one-platform file
        packages_service.add_item(db, package.id, "document", text=f"{n} " + "م" * 1000,
                                  file_id=f"DOC{n}", platform=Platform.TELEGRAM)
    disp.handle_update(callback_update(3, CHAT, OWNER, f"a:pkg:add:{package.id}"))
    disp.handle_update(message_update(4, CHAT, OWNER, "یکی دیگر"))
    limit = P.ITEM_LIMIT.format(n=packages_service.MAX_ITEMS)
    assert last_text(client).startswith(f"⚠️ {limit}")
    assert len(packages_service.items(db, package.id)) == packages_service.MAX_ITEMS

    # A full package still fits one message and one keyboard, for the coach and the student.
    packages_service.assign(db, package.id, [negar.id], notify=False)
    student, student_client = make_dispatcher()
    register(student, 7001, 5001, phone=NEGAR)
    for disp_, client_, chat, user, data in (
        (disp, client, CHAT, OWNER, f"a:pkg:view:{package.id}"),
        (student, student_client, 7001, 5001, f"pk:{package.id}"),
    ):
        disp_.handle_update(callback_update(5, chat, user, data))
        assert len(last_text(client_)) <= 4096
        assert len(button_texts(last_markup(client_))) < 100


def test_reordering_items(db):
    package, doc, video, note = _package(db)
    disp, client = make_dispatcher()
    for update_id in (1, 2, 3):  # the third press finds it on top already
        disp.handle_update(callback_update(update_id, CHAT, OWNER, f"a:pkg:up:{note.id}"))
    assert last_text(client).startswith(P.ITEM_TITLE.format(package=package.title, pos=1, total=3))
    disp.handle_update(callback_update(4, CHAT, OWNER, f"a:pkg:down:{doc.id}"))
    db.expire_all()
    assert [i.id for i in packages_service.items(db, package.id)] == [note.id, video.id, doc.id]


def test_item_text_and_title_edits_and_a_delete_that_asks_first(db):
    package, doc, video, note = _package(db)
    note_id = note.id  # a deleted row's object cannot be read back
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:pkg:ititle:{video.id}"))
    disp.handle_update(message_update(2, CHAT, OWNER, "جلسه ۱"))
    assert last_text(client).startswith(P.SAVED)
    disp.handle_update(callback_update(3, CHAT, OWNER, f"a:pkg:itext:{video.id}"))
    assert P.BTN_CLEAR_TEXT in button_texts(last_markup(client))  # a caption may go
    disp.handle_update(message_update(4, CHAT, OWNER, "اسکات با هالتر"))
    db.expire_all()
    edited = packages_service.get_item(db, video.id)
    assert (edited.title, edited.text) == ("جلسه ۱", "اسکات با هالتر")
    assert packages_service.item_label(edited) == "جلسه ۱"

    disp.handle_update(callback_update(5, CHAT, OWNER, f"a:pkg:idel_confirm:{note_id}"))
    assert A.BTN_YES_DELETE in button_texts(last_markup(client))
    assert packages_service.find_item(db, note_id) is not None  # nothing deleted yet
    disp.handle_update(callback_update(6, CHAT, OWNER, f"a:pkg:idel:{note_id}"))
    assert last_text(client).startswith(P.ITEM_DELETED)
    db.expunge_all()
    assert packages_service.find_item(db, note_id) is None


# --- sending ---


def test_sending_to_several_students_tells_each_once(db, notified):
    sara = _student(db, "سارا", SARA, StudentType.IN_PERSON)
    negar = _student(db, "نگار", NEGAR)
    mina = _student(db, "مینا", MINA)
    package, *_ = _package(db)
    disp, client = make_dispatcher()

    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:pkg:send:{package.id}"))
    labels = button_texts(last_markup(client))
    assert labels.index("⚪ 🌐 نگار") < labels.index("⚪ 🏋️ سارا")  # online students first
    disp.handle_update(message_update(2, CHAT, OWNER, "نگار"))  # typing a name narrows it
    labels = button_texts(last_markup(client))
    assert "⚪ 🌐 نگار" in labels and "⚪ 🏋️ سارا" not in labels
    disp.handle_update(callback_update(3, CHAT, OWNER, f"a:pkg:tg:{package.id}:{negar.id}"))
    disp.handle_update(callback_update(4, CHAT, OWNER, f"a:pkg:sall:{package.id}"))
    disp.handle_update(callback_update(5, CHAT, OWNER, f"a:pkg:tg:{package.id}:{sara.id}"))
    labels = button_texts(last_markup(client))
    assert "🟢 🌐 نگار" in labels and "🟢 🏋️ سارا" in labels  # the filter kept the pick
    assert P.BTN_SEND_TO.format(n=2) in labels

    disp.handle_update(callback_update(6, CHAT, OWNER, f"a:pkg:sgo:{package.id}"))
    assert last_text(client).startswith(P.SENT.format(n=2))
    message = P.NOTIFY_ASSIGNED.format(title=package.title)
    assert sorted(notified) == sorted([(negar.id, message), (sara.id, message)])

    # Again: those two have it now and cannot be picked twice.
    disp.handle_update(callback_update(7, CHAT, OWNER, f"a:pkg:send:{package.id}"))
    disp.handle_update(callback_update(8, CHAT, OWNER, f"a:pkg:tg:{package.id}:{negar.id}"))
    labels = button_texts(last_markup(client))
    assert "✅ 🌐 نگار — دارد" in labels and not any(b.startswith("✅ ارسال") for b in labels)
    disp.handle_update(callback_update(9, CHAT, OWNER, f"a:pkg:tg:{package.id}:{mina.id}"))
    disp.handle_update(callback_update(10, CHAT, OWNER, f"a:pkg:sgo:{package.id}"))
    assert [person_id for person_id, _ in notified].count(mina.id) == 1
    assert len(notified) == 3

    # Sending the same people again is a no-op: no new rows, no new messages.
    assert packages_service.assign(db, package.id, [negar.id, sara.id, mina.id]) == []
    assert len(notified) == 3
    db.expire_all()
    rows = db.scalar(select(func.count()).select_from(PackageAssignment))
    assert rows == 3


def test_a_stale_picker_tap_starts_over_and_says_so(db):
    negar = _student(db, "نگار", NEGAR)
    package, *_ = _package(db)
    disp, client = make_dispatcher()  # a fresh process: no picker in progress
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:pkg:tg:{package.id}:{negar.id}"))
    assert last_text(client).startswith(P.PICK_EXPIRED)
    assert "⚪ 🌐 نگار" in button_texts(last_markup(client))


def test_an_empty_or_inactive_package_is_not_sent(db, notified):
    negar = _student(db, "نگار", NEGAR)
    empty = packages_service.create(db, title="خالی")
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:pkg:send:{empty.id}"))
    assert last_text(client).startswith(f"⚠️ {P.SEND_EMPTY}")
    package, *_ = _package(db)
    packages_service.set_active(db, package.id, False)
    disp.handle_update(callback_update(2, CHAT, OWNER, f"a:pkg:give:{negar.id}:{package.id}"))
    assert last_text(client).startswith(f"⚠️ {P.SEND_INACTIVE}")
    assert notified == []


def test_one_student_from_their_programs_screen(db, notified):
    negar = _student(db, "نگار", NEGAR)
    package, *_ = _package(db)
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:plans:client:{negar.id}"))
    assert P.BTN_GIVE in button_texts(last_markup(client))
    disp.handle_update(callback_update(2, CHAT, OWNER, f"a:pkg:for:{negar.id}"))
    assert last_text(client) == P.ASK_PICK_PACKAGE.format(name="نگار")
    disp.handle_update(callback_update(3, CHAT, OWNER, f"a:pkg:give:{negar.id}:{package.id}"))
    screen = last_text(client)
    assert screen.startswith(P.GIVEN.format(title=package.title, name="نگار"))
    assert A.PROGRAMS_OF.format(name="نگار") in screen  # back on her programs screen
    assert f"📦 {package.title}" in button_texts(last_markup(client))
    assert len(notified) == 1

    disp.handle_update(callback_update(4, CHAT, OWNER, f"a:pkg:give:{negar.id}:{package.id}"))
    assert last_text(client).startswith(P.ALREADY_HAS.format(name="نگار"))
    assert len(notified) == 1

    # Taking it away asks first, and lands back on her screen.
    (given,) = packages_service.assignments_for_person(db, negar.id)
    disp.handle_update(callback_update(5, CHAT, OWNER, f"a:pkg:rvc:{given.id}:s"))
    assert P.BTN_YES_REVOKE in button_texts(last_markup(client))
    assert packages_service.open_for(db, package.id, negar.id) is not None  # not yet
    disp.handle_update(callback_update(6, CHAT, OWNER, f"a:pkg:rv:{given.id}:s"))
    assert last_text(client).startswith(P.REVOKED.format(name="نگار", title=package.title))
    assert f"📦 {package.title}" not in button_texts(last_markup(client))
    db.expire_all()
    assert packages_service.open_for(db, package.id, negar.id) is None


def test_recipients_list_and_revoking_from_it(db):
    negar = _student(db, "نگار", NEGAR)
    package, *_ = _package(db)
    packages_service.assign(db, package.id, [negar.id], notify=False)
    (given,) = packages_service.recipients(db, package.id)
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:pkg:rcp:{package.id}"))
    assert last_text(client).startswith(P.RECIPIENTS_TITLE.format(title=package.title, n=1))
    assert "👤 نگار" in button_texts(last_markup(client))
    disp.handle_update(callback_update(2, CHAT, OWNER, f"a:pkg:rv:{given.id}"))
    assert last_text(client).startswith(P.REVOKED.format(name="نگار", title=package.title))
    assert P.NO_RECIPIENTS in last_text(client)


# --- the student's side ---


def test_student_opens_the_package_and_each_item_arrives_one_call(db):
    negar = _student(db, "نگار", NEGAR)
    package, doc, video, note = _package(db)
    packages_service.assign(db, package.id, [negar.id], notify=False)
    diet = plans_service.create_type(db, title="تغذیه")
    program = plans_service.create_assignment(
        db, person_id=negar.id, plan_type_id=diet.id, platform_file_id="PLAN1",
        file_platform=Platform.TELEGRAM, file_kind="document", notify=False,
    )
    disp, client = make_dispatcher()
    register(disp, 7001, 5001, phone=NEGAR)

    disp.handle_update(callback_update(1, 7001, 5001, "prg"))
    labels = button_texts(last_markup(client))
    assert labels[0] == f"📦 {package.title} · 3 مورد"  # packages first…
    assert labels[1].startswith("📎 تغذیه")  # …then single programs, unchanged

    disp.handle_update(callback_update(2, 7001, 5001, f"pk:{package.id}"))
    assert last_text(client).startswith(f"📦 {package.title}\n\nهشت هفته غذا و تمرین")
    assert button_texts(last_markup(client))[:3] == [
        "📎 برنامه غذایی هفته اول", "🎬 هفته ۱ — اسکات", "📝 نکات مهم: روزی ۸ لیوان آب",
    ]

    client.sent.clear()
    disp.handle_update(callback_update(3, 7001, 5001, f"pk:{package.id}:{video.id}"))
    assert _file_sends(client) == [("send_video_id", "VID1")]  # one call, the right method
    assert client.sent[0]["caption"] == "هفته ۱ — اسکات\n۳ ست ۱۲ تکرار"
    assert last_text(client) == P.ITEM_SENT.format(label="هفته ۱ — اسکات")
    assert "📎 برنامه غذایی هفته اول" in button_texts(last_markup(client))  # next is a tap away

    client.sent.clear()
    disp.handle_update(callback_update(4, 7001, 5001, f"pk:{package.id}:{doc.id}"))
    assert _file_sends(client) == [("send_document_id", "DOC1")]

    client.sent.clear()
    disp.handle_update(callback_update(5, 7001, 5001, f"pk:{package.id}:{note.id}"))
    assert _file_sends(client) == []
    text_message = next(m for m in client.sent if m.get("text") == note.text)
    assert text_message["message_id"] not in client.deleted  # it stays in the chat

    client.sent.clear()  # a single program still arrives as before
    disp.handle_update(callback_update(6, 7001, 5001, f"prg:{program.id}"))
    assert _file_sends(client) == [("send_document_id", "PLAN1")]


def test_a_bale_student_gets_the_text_until_the_bale_copy_is_added(db):
    negar = _student(db, "نگار", NEGAR)
    package, doc, video, note = _package(db)
    packages_service.assign(db, package.id, [negar.id], notify=False)
    bale, bale_client = make_dispatcher(Platform.BALE)
    register(bale, 8001, 6001, phone=NEGAR)

    bale_client.sent.clear()
    bale.handle_update(callback_update(1, 8001, 6001, f"pk:{package.id}:{video.id}"))
    assert _file_sends(bale_client) == []  # Telegram's file_id is useless on Bale
    words = next(m["text"] for m in bale_client.sent if video.text in (m.get("text") or ""))
    assert P.FILE_ON_OTHER.format(platform="تلگرام") in words

    # On Telegram, the coach is told how; on Bale, the same button records the copy.
    tg, tg_client = make_dispatcher()
    tg.handle_update(callback_update(2, CHAT, OWNER, f"a:pkg:item:{video.id}"))
    assert P.BTN_COPY.format(platform="بله") in button_texts(last_markup(tg_client))
    tg.handle_update(callback_update(3, CHAT, OWNER, f"a:pkg:copy:{video.id}"))
    assert last_text(tg_client) == P.COPY_HOWTO.format(have="تلگرام", missing="بله")

    coach, coach_client = make_dispatcher(Platform.BALE)
    coach.handle_update(callback_update(4, CHAT, BALE_OWNER, f"a:pkg:item:{video.id}"))
    assert P.BTN_ADD_COPY_HERE.format(platform="بله") in button_texts(last_markup(coach_client))
    coach.handle_update(callback_update(5, CHAT, BALE_OWNER, f"a:pkg:copy:{video.id}"))
    coach.handle_update(_file_update(6, "document", "BDOC", user=BALE_OWNER))  # wrong kind
    assert last_text(coach_client).startswith(
        f"⚠️ {P.COPY_WRONG_KIND.format(kind=P.KIND_NAMES['video'])}"
    )
    coach.handle_update(_file_update(7, "video", "BVID", user=BALE_OWNER))
    assert last_text(coach_client).startswith(P.COPY_SAVED.format(platform="بله"))
    db.expire_all()
    copied = packages_service.get_item(db, video.id)
    assert (copied.telegram_file_id, copied.bale_file_id) == ("VID1", "BVID")

    bale_client.sent.clear()
    bale.handle_update(callback_update(8, 8001, 6001, f"pk:{package.id}:{video.id}"))
    assert _file_sends(bale_client) == [("send_video_id", "BVID")]


def test_a_text_program_stays_in_the_chat(db):
    """Shared delivery path: a single program's text (or a note past the caption
    limit) used to be sent as the chat's tracked screen, so the «این هم برنامه‌ات»
    message right after it deleted the program the student came for."""
    sara = _student(db, "سارا", SARA)
    diet = plans_service.create_type(db, title="تغذیه")
    program = plans_service.create_assignment(
        db, person_id=sara.id, plan_type_id=diet.id, coach_note="صبحانه: جو دوسر", notify=False
    )
    disp, client = make_dispatcher()
    register(disp, 7002, 5002, phone=SARA)
    disp.handle_update(callback_update(1, 7002, 5002, f"prg:{program.id}"))
    sent = next(m for m in client.sent if "صبحانه: جو دوسر" in (m.get("text") or ""))
    assert sent["message_id"] not in client.deleted
    assert last_text(client) == texts.PROGRAM_SENT


def test_a_failed_send_still_gives_the_words(db, monkeypatch):
    package, doc, video, note = _package(db)
    disp, client = make_dispatcher()

    def refuse(*args, **kwargs):
        raise BotApiError("telegram API sendVideo failed")

    monkeypatch.setattr(client, "send_video_id", refuse)
    client_flow._deliver_item(disp.ctx, packages_service.get_item(db, video.id), 7001)
    (message,) = client.sent
    assert video.text in message["text"] and P.FILE_FAILED in message["text"]


def test_a_long_item_text_never_takes_the_file_down(db):
    """Captions stop at 1024 characters and messages at 4096."""
    package, doc, video, note = _package(db)
    long_text = "\n".join(f"حرکت {i}: ۳ ست ۱۲ تکرار، استراحت ۶۰ ثانیه" for i in range(200))
    packages_service.update_item(db, video.id, text=long_text, title="هفته ۱")
    disp, client = make_dispatcher()
    client_flow._deliver_item(disp.ctx, packages_service.get_item(db, video.id), 7001)
    first, *rest = client.sent
    assert first["method"] == "send_video_id" and first["caption"] == "هفته ۱"
    assert rest and all(len(m["text"]) <= 4096 for m in rest)
    assert "".join(m["text"] for m in rest).count("حرکت 199") == 1


def test_a_deactivated_package_is_hidden_from_students(db):
    negar = _student(db, "نگار", NEGAR)
    package, doc, *_ = _package(db)
    packages_service.assign(db, package.id, [negar.id], notify=False)
    coach, coach_client = make_dispatcher()
    coach.handle_update(callback_update(1, CHAT, OWNER, f"a:pkg:toggle:{package.id}"))
    assert last_text(coach_client).startswith(P.DEACTIVATED)

    disp, client = make_dispatcher()
    register(disp, 7001, 5001, phone=NEGAR)
    disp.handle_update(callback_update(2, 7001, 5001, "prg"))
    assert last_text(client) == texts.NO_PROGRAMS  # nothing else to show
    disp.handle_update(callback_update(3, 7001, 5001, f"pk:{package.id}"))
    assert last_text(client) == texts.NOT_FOUND
    client.sent.clear()
    disp.handle_update(callback_update(4, 7001, 5001, f"pk:{package.id}:{doc.id}"))
    assert _file_sends(client) == [] and last_text(client) == texts.NOT_FOUND

    coach.handle_update(callback_update(5, CHAT, OWNER, f"a:pkg:toggle:{package.id}"))
    disp.handle_update(callback_update(6, 7001, 5001, "prg"))
    assert button_texts(last_markup(client))[0] == f"📦 {package.title} · 3 مورد"


def test_foreign_and_tampered_ids_are_refused(db):
    negar = _student(db, "نگار", NEGAR)
    sara = _student(db, "سارا", SARA)
    mine, my_doc, *_ = _package(db, title="مال نگار")
    theirs, their_doc, *_ = _package(db, title="مال سارا")
    packages_service.assign(db, mine.id, [negar.id], notify=False)
    packages_service.assign(db, theirs.id, [sara.id], notify=False)
    disp, client = make_dispatcher()
    register(disp, 7001, 5001, phone=NEGAR)

    for update_id, data in enumerate([
        f"pk:{theirs.id}",  # someone else's package
        f"pk:{theirs.id}:{their_doc.id}",
        f"pk:{mine.id}:{their_doc.id}",  # her package, another package's item
        "pk:999999",
        f"pk:{mine.id}:abc",
        f"pk:{mine.id}:{my_doc.id}:9",
        f"pk:{mine.id}:{10 ** 30}",  # past any row id
    ], start=1):
        client.sent.clear()
        disp.handle_update(callback_update(update_id, 7001, 5001, data))
        assert last_text(client) == texts.NOT_FOUND, data
        assert _file_sends(client) == [], data

    disp.handle_update(callback_update(20, 7001, 5001, "pk:abc"))  # no id: her list
    assert button_texts(last_markup(client))[0] == "📦 مال نگار · 3 مورد"
    disp.handle_update(callback_update(21, 7001, 5001, f"a:pkg:view:{mine.id}"))
    assert client.answered[-1]["text"] == texts.ACCESS_DENIED  # admin screens: owners only

    (given,) = packages_service.assignments_for_person(db, negar.id)
    packages_service.unassign(db, given.id)
    disp.handle_update(callback_update(22, 7001, 5001, f"pk:{mine.id}"))
    assert last_text(client) == texts.NOT_FOUND  # revoked


# --- guards ---


def test_deleting_asks_first_and_is_refused_once_sent(db):
    negar = _student(db, "نگار", NEGAR)
    draft, *_ = _package(db, title="پیش‌نویس")
    draft_id = draft.id  # a deleted row's object cannot be read back
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:pkg:del_confirm:{draft_id}"))
    assert A.BTN_YES_DELETE in button_texts(last_markup(client))
    assert packages_service.find(db, draft_id) is not None  # nothing deleted yet
    disp.handle_update(callback_update(2, CHAT, OWNER, f"a:pkg:del:{draft_id}"))
    assert last_text(client).startswith(P.DELETED)
    db.expunge_all()
    assert packages_service.find(db, draft_id) is None
    assert packages_service.items(db, draft_id) == []  # its items went with it

    sent, *_ = _package(db, title="ارسال‌شده")
    packages_service.assign(db, sent.id, [negar.id], notify=False)
    (given,) = packages_service.recipients(db, sent.id)
    packages_service.unassign(db, given.id)  # nobody has it now — it was still sent
    before = len(client.sent)
    disp.handle_update(callback_update(3, CHAT, OWNER, f"a:pkg:del_confirm:{sent.id}"))
    assert len(client.sent) == before + 1  # one screen, the refusal flashed on top
    assert last_text(client).startswith(f"⚠️ {P.DELETE_REFUSED}")
    disp.handle_update(callback_update(4, CHAT, OWNER, f"a:pkg:del:{sent.id}"))  # an old button
    assert last_text(client).startswith(f"⚠️ {P.DELETE_REFUSED}")
    db.expire_all()
    assert packages_service.find(db, sent.id) is not None


def test_deleting_a_student_takes_their_package_access(db):
    """SQLite enforces no foreign keys and may hand the freed id to the next
    student: an orphaned row would give them someone else's package."""
    negar = _student(db, "نگار", NEGAR)
    package, *_ = _package(db)
    packages_service.assign(db, package.id, [negar.id], notify=False)
    student_id = negar.id
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:students:del:{student_id}"))
    db.expire_all()
    assert db.get(Person, student_id) is None
    left = db.scalar(select(func.count()).select_from(PackageAssignment).where(
        PackageAssignment.person_id == student_id
    ))
    assert left == 0
    newcomer = persons_service.create(db, name="تازه‌وارد")
    assert packages_service.list_for_person(db, newcomer.id) == []
    disp.handle_update(callback_update(2, CHAT, OWNER, f"a:pkg:rcp:{package.id}"))
    assert P.NO_RECIPIENTS in last_text(client)


def test_a_stale_admin_button_lands_on_the_list(db):
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, "a:pkg:view:4242"))
    assert last_text(client).startswith(f"⚠️ {P.NOT_FOUND}")
    assert P.BTN_NEW in button_texts(last_markup(client))


def test_callbacks_fit_in_64_bytes_even_with_huge_ids(db):
    negar = _student(db, "نگار", NEGAR)
    package, doc, video, note = _package(db)
    packages_service.assign(db, package.id, [negar.id], notify=False)
    coach, coach_client = make_dispatcher()
    student, student_client = make_dispatcher()
    register(student, 7001, 5001, phone=NEGAR)
    screens = [
        (coach, coach_client, CHAT, OWNER, f"a:pkg:view:{package.id}"),
        (coach, coach_client, CHAT, OWNER, f"a:pkg:item:{video.id}"),
        (coach, coach_client, CHAT, OWNER, f"a:pkg:send:{package.id}"),
        (coach, coach_client, CHAT, OWNER, f"a:pkg:rcp:{package.id}"),
        (coach, coach_client, CHAT, OWNER, f"a:plans:client:{negar.id}"),
        (student, student_client, 7001, 5001, f"pk:{package.id}"),
    ]
    for update_id, (disp, client, chat, user, data) in enumerate(screens, start=1):
        disp.handle_update(callback_update(update_id, chat, user, data))
        for row in last_markup(client)["inline_keyboard"]:
            for button in row:
                widest = re.sub(r"\d+", "9" * 10, button["callback_data"])  # 10-digit ids
                assert len(widest.encode()) <= 64, button["callback_data"]
