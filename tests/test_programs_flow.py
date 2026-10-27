"""«📄 مدیریت برنامه‌ها» end to end: the hub, sending a training video, the
guards against empty or file-less programs, and delivery to the student."""

from app.bots.common import client_flow, formatting
from app.copy import admin_texts as A
from app.models import Platform, StudentType
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

OWNER = 111
CHAT = 900
STUDENT_PHONE = "09125550000"


def _video_update(update_id, file_id="VID1", caption=None):
    message = {
        "message_id": 10,
        "chat": {"id": CHAT},
        "from": {"id": OWNER, "first_name": "مربی"},
        "video": {"file_id": file_id, "file_name": "squat.mp4", "duration": 30},
    }
    if caption:
        message["caption"] = caption
    return {"update_id": update_id, "message": message}


def _setup(db):
    student = persons_service.create(
        db, name="نگار رضایی", phone=STUDENT_PHONE, student_type=StudentType.ONLINE
    )
    diet = plans_service.create_type(db, title="تغذیه")
    training = plans_service.create_type(db, title="برنامه تمرینی")
    return student, diet, training


def test_hub_offers_sending_and_the_type_catalog(db):
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, "a:plans"))
    assert button_texts(last_markup(client))[:2] == [A.BTN_ASSIGN_PLAN, A.BTN_PLAN_TYPES]


def test_training_video_reaches_the_student(db):
    student, _, training = _setup(db)
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, "a:plans:pick"))
    assert "🌐 نگار رضایی" in button_texts(last_markup(client))

    disp.handle_update(callback_update(2, CHAT, OWNER, f"a:plans:assign:{student.id}"))
    picker = button_texts(last_markup(client))
    assert "برنامه تمرینی" in picker and A.BTN_NEW_PLAN_TYPE in picker

    disp.handle_update(callback_update(3, CHAT, OWNER, f"a:plans:type:{student.id}:{training.id}"))
    # The video comes straight away, its caption as the note — no extra step.
    disp.handle_update(_video_update(4, caption="هفته اول — اسکات"))
    assert last_text(client) == A.PLAN_ASSIGNED

    (program,) = plans_service.list_assignments(db, person_id=student.id)
    assert program.file_kind == "video" and program.platform_file_id == "VID1"
    assert program.coach_note == "هفته اول — اسکات"
    assert formatting.program_label(program).startswith("🎬 برنامه تمرینی · هفته اول")

    # The student opens it: one sendVideo call, no document/photo attempts first.
    sdisp, sclient = make_dispatcher()
    register(sdisp, 7001, 5001, phone=STUDENT_PHONE)
    sdisp.handle_update(callback_update(5, 7001, 5001, f"prg:{program.id}"))
    sent = [m["method"] for m in sclient.sent]
    assert "send_video_id" in sent and "send_document_id" not in sent


def test_text_where_the_file_belongs_is_asked_again(db):
    student, diet, _ = _setup(db)
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:plans:type:{student.id}:{diet.id}"))
    disp.handle_update(message_update(2, CHAT, OWNER, "صبحانه: جو دوسر"))  # the note
    disp.handle_update(message_update(3, CHAT, OWNER, "اینم فایل"))  # text, not a file
    assert A.PLAN_FILE_EXPECTED in last_text(client)
    assert plans_service.list_assignments(db, person_id=student.id) == []


def test_an_empty_program_is_never_sent(db):
    student, diet, _ = _setup(db)
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:plans:type:{student.id}:{diet.id}"))
    disp.handle_update(callback_update(2, CHAT, OWNER, "a:plans:note_skip"))
    disp.handle_update(callback_update(3, CHAT, OWNER, "a:plans:file_skip"))
    assert last_text(client) == A.PLAN_EMPTY
    assert plans_service.list_assignments(db, person_id=student.id) == []

    disp.handle_update(message_update(4, CHAT, OWNER, "صبحانه: جو دوسر و شیر"))
    (program,) = plans_service.list_assignments(db, person_id=student.id)
    assert program.coach_note == "صبحانه: جو دوسر و شیر" and program.platform_file_id is None


def test_a_new_type_can_be_made_mid_send(db):
    student, _, _ = _setup(db)
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:plans:new_type_for:{student.id}"))
    disp.handle_update(message_update(2, CHAT, OWNER, "برنامه حرکات اصلاحی"))
    assert last_text(client) == A.ASK_PLAN_NOTE  # straight on with the send
    disp.handle_update(message_update(3, CHAT, OWNER, "روزی دو بار"))
    disp.handle_update(callback_update(4, CHAT, OWNER, "a:plans:file_skip"))
    (program,) = plans_service.list_assignments(db, person_id=student.id)
    assert program.plan_type.title == "برنامه حرکات اصلاحی"


def test_deleting_a_type_asks_first_and_explains_a_refusal(db):
    student, diet, training = _setup(db)
    plans_service.create_assignment(db, person_id=student.id, plan_type_id=diet.id,
                                    coach_note="x", notify=False)
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:plans:del_type:{training.id}"))
    assert A.BTN_YES_DELETE in button_texts(last_markup(client))
    assert plans_service.get_type_by_key(db, training.key) is not None  # not yet

    before = len(client.sent)
    disp.handle_update(callback_update(2, CHAT, OWNER, f"a:plans:delete_type:{diet.id}"))
    assert len(client.sent) == before + 1  # one screen, the refusal flashed on top
    assert last_text(client).startswith("⚠️")


def test_a_long_note_never_takes_the_file_down(db):
    """Captions stop at 1024 characters and messages at 4096: the file goes out
    with a short caption and the note follows in pieces."""
    student, _, training = _setup(db)
    long_note = "\n".join(f"حرکت {i}: ۳ ست ۱۲ تکرار، استراحت ۶۰ ثانیه" for i in range(200))
    program = plans_service.create_assignment(
        db, person_id=student.id, plan_type_id=training.id, coach_note=long_note,
        platform_file_id="DOC9", file_platform=Platform.TELEGRAM, file_kind="document",
        notify=False,
    )
    disp, client = make_dispatcher()
    caption = formatting.format_program_caption(program)
    client_flow._deliver_program(disp.ctx, program, 7001, caption)
    doc, *notes = client.sent
    assert doc["method"] == "send_document_id" and len(doc["caption"]) <= 1024
    assert notes and all(len(m["text"]) <= 4096 for m in notes)
    assert "".join(m["text"] for m in notes).count("حرکت 199") == 1
