"""Admin section: attendance recording (append-only, with confirm)."""

from __future__ import annotations

from datetime import date

from app.admin import common
from app.admin.common import AdminReq
from app.copy import admin_texts as A
from app.models import AttendanceStatus, CourseStatus
from app.services import attendance as attendance_service
from app.services import courses as courses_service
from app.services import persons as persons_service


def handle_callback(req: AdminReq, args: str) -> None:
    action, _, rest = (args or "").partition(":")
    if action == "client" and rest.isdigit():
        _pick_course(req, int(rest))
    elif action == "course" and rest.isdigit():
        common.prompt(req, A.ASK_ATTEND_DATE, "attend:date", {"course_id": int(rest)})
    elif action == "outcome":
        _set_outcome(req, rest)
    elif action == "note_skip":
        _save(req, note=None)
    else:
        common.render(req, A.ATTEND_TITLE, common.with_back([]))


def handle_message(req: AdminReq, message: dict, substep: str, state) -> None:
    text = (message.get("text") or "").strip()
    data = state.data
    if substep == "date":
        session_date = common.parse_date(text)
        if session_date is None:
            common.prompt(req, A.INVALID_DATE, "attend:date", data)
            return
        data["date"] = session_date.isoformat()
        common.prompt(
            req, A.ASK_ATTEND_OUTCOME, "attend:outcome_wait", data,
            keyboard=_outcome_keyboard(),
        )
    elif substep == "note":
        _save(req, note=text or None)
    else:
        common.clear(req)


def _outcome_keyboard() -> dict:
    rows = [
        [common.button(attendance_service.status_label(status), "attend", "outcome", status.name)]
        for status in attendance_service.all_statuses()
    ]
    return common.inline(rows + [[common.home_button()]])


def _set_outcome(req: AdminReq, status_name: str) -> None:
    state = req.store.get(req.ctx.platform, req.chat_id)
    if state is None or status_name not in AttendanceStatus.__members__:
        common.render(req, A.ATTEND_TITLE, common.with_back([]))
        return
    state.data["status"] = status_name
    common.prompt(
        req, A.ASK_ATTEND_NOTE, "attend:note", state.data,
        keyboard=common.skip_keyboard(("attend", "note_skip")),
    )


def _save(req: AdminReq, note: str | None) -> None:
    state = req.store.get(req.ctx.platform, req.chat_id)
    if state is None or "date" not in state.data or "status" not in state.data:
        common.render(req, A.ATTEND_TITLE, common.with_back([]))
        return
    data = state.data
    attendance_service.record(
        req.db,
        data["course_id"],
        date.fromisoformat(data["date"]),
        AttendanceStatus[data["status"]],
        note=note,
        created_by=req.user_id,
    )
    course_id = data["course_id"]
    common.clear(req)
    common.render(req, A.ATTEND_SAVED, common.back_home("courses", "view", course_id))


def _pick_course(req: AdminReq, client_id: int) -> None:
    persons_service.get(req.db, client_id)
    courses = [
        c for c in courses_service.list_courses(req.db, client_id=client_id)
        if c.status != CourseStatus.FINISHED
    ]
    rows = [
        [common.button(
            f"{c.class_type.title} | {courses_service.remaining_sessions(req.db, c)}",
            "attend", "course", c.id,
        )]
        for c in courses
    ]
    body = A.ATTEND_PICK_COURSE if rows else A.NOTHING
    common.render(req, body, common.with_back(rows, ("students", "view", client_id)))
