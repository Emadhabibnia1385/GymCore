"""Admin section: the session grid — tap a row, pick an outcome.

The screen is the coach's paper table (weekday · date · outcome, three glass
buttons per row). Every cell of a row carries the same callback, so tapping
anywhere on the row opens that session's outcome picker: ✅ حاضر / 🔴 غیبت /
🟡 مجاز, plus 🔵 لغو مربی and ⚪ تعطیلی, with an optional note.

The grid itself is derived, never stored (app/services/schedule.py), and every
outcome is appended through the attendance service, so history stays
append-only and a re-tap on an already-recorded row is a correction.
"""

from __future__ import annotations

from datetime import date

from app.admin import common
from app.admin.common import AdminReq
from app.bots.common import grid
from app.copy import admin_texts as A
from app.core.exceptions import DomainError
from app.models import AttendanceStatus, CourseStatus
from app.repositories.pagination import paginate
from app.services import attendance as attendance_service
from app.services import courses as courses_service
from app.services import persons as persons_service
from app.services import schedule as schedule_service

_PER_PAGE = 6
_NOTE_STEP = "attend:note"


def handle_callback(req: AdminReq, args: str) -> None:
    action, _, rest = (args or "").partition(":")
    if action == "client" and rest.isdigit():
        _pick_course(req, int(rest))
    elif action == "page":
        _pick_active(req, page=common.parse_count(rest) or 1)
    elif action == "course":
        course_id, _, page = rest.partition(":")
        if course_id.isdigit():
            _grid(req, int(course_id), int(page) if page.isdigit() else None)
        else:
            _pick_active(req)
    elif action == "slot":
        course_id, _, token = rest.partition(":")
        session_date = grid.parse_date_token(token)
        if course_id.isdigit() and session_date is not None:
            _slot(req, int(course_id), session_date)
        else:
            _pick_active(req)
    elif action == "set":
        _set(req, rest)
    elif action == "note":
        course_id, _, token = rest.partition(":")
        session_date = grid.parse_date_token(token)
        if course_id.isdigit() and session_date is not None:
            common.prompt(
                req, A.ASK_ATTEND_NOTE, _NOTE_STEP,
                {"course_id": int(course_id), "date": token},
            )
    elif action == "extra" and rest.isdigit():
        common.prompt(req, A.ASK_ATTEND_DATE, "attend:extra", {"course_id": int(rest)})
    else:
        _pick_active(req)


def handle_message(req: AdminReq, message: dict, substep: str, state) -> None:
    text = (message.get("text") or "").strip()
    data = state.data
    if substep == "note":
        session_date = grid.parse_date_token(data.get("date", ""))
        if session_date is None:
            common.clear(req)
            _pick_active(req)
            return
        # Stage the note, then re-open the picker so the next tap saves both.
        _slot(req, data["course_id"], session_date, staged_note=text or None)
    elif substep == "extra":
        session_date = common.parse_date(text)
        if session_date is None:
            common.prompt(req, A.INVALID_DATE, "attend:extra", data)
            return
        common.clear(req)
        _slot(req, data["course_id"], session_date)
    else:
        common.clear(req)
        _pick_active(req)


# --- pickers ---


def _pick_active(req: AdminReq, page: int = 1) -> None:
    """All active courses, so «ثبت حضور و غیاب» is one tap from the main menu."""
    result = paginate(
        req.db,
        courses_service.list_stmt(status=CourseStatus.ACTIVE),
        page=page,
        per_page=_PER_PAGE,
    )
    rows = [
        [common.button(
            grid.course_button_label(req.db, course, with_name=True),
            "attend", "course", course.id,
        )]
        for course in result.items
    ]
    body = f"{A.ATTEND_TITLE}\n{A.ATTEND_PICK_COURSE}" if rows else A.ATTEND_NO_ACTIVE
    common.render(req, body, common.pager(rows, result.page, result.pages, ("attend",)))


def _pick_course(req: AdminReq, client_id: int) -> None:
    """The grid entry point from a student's profile."""
    persons_service.get(req.db, client_id)
    courses = [
        c for c in courses_service.list_courses(req.db, client_id=client_id)
        if c.status != CourseStatus.FINISHED
    ]
    if len(courses) == 1:  # the common case — skip a pointless menu
        _grid(req, courses[0].id)
        return
    rows = [
        [common.button(grid.course_button_label(req.db, c), "attend", "course", c.id)]
        for c in courses
    ]
    body = A.ATTEND_PICK_COURSE if rows else A.NOTHING
    common.render(req, body, common.with_back(rows, ("students", "view", client_id)))


# --- the grid ---


def _grid(
    req: AdminReq, course_id: int, page: int | None = None, flash: str | None = None
) -> None:
    course = courses_service.get(req.db, course_id)
    slots = schedule_service.build(req.db, course)
    if not slots:
        common.render(
            req, A.NOTHING, common.back_home("students", "view", course.client_id)
        )
        return
    visible, page, pages = grid.page_slice(slots, page or grid.default_page(slots))
    # The confirmation rides along in the grid header — one screen, never two.
    lead = f"{flash}\n\n" if flash else ""
    body = f"{lead}{grid.header(req.db, course, page, pages, for_admin=True)}\n\n{A.GRID_HINT}"
    rows = grid.rows(
        visible,
        lambda slot: common.cb_data("attend", "slot", course.id, grid.date_token(slot.date)),
    )
    nav: list[dict] = []
    if page > 1:
        nav.append(common.button(A.PREV, "attend", "course", course.id, page - 1))
    if page < pages:
        nav.append(common.button(A.NEXT, "attend", "course", course.id, page + 1))
    if nav:
        rows.append(nav)
    rows.append([common.button(A.BTN_EXTRA_SESSION, "attend", "extra", course.id)])
    common.render(req, body, common.with_back(rows, ("students", "view", course.client_id)))


def _slot(
    req: AdminReq, course_id: int, session_date, staged_note: str | None = None
) -> None:
    """The outcome picker for one session (also used for off-schedule dates)."""
    from app.core.jalali import format_jalali

    course = courses_service.get(req.db, course_id)
    slots = schedule_service.build(req.db, course)
    slot = schedule_service.find_slot(slots, session_date)

    lines = [
        A.SLOT_TITLE.format(
            weekday=schedule_service.weekday_name(session_date),
            date=format_jalali(session_date),
        ),
        f"🏷 {course.class_type.title} · 👤 {course.client.name}",
        f"{A.SLOT_CURRENT}: "
        + (attendance_service.status_label(slot.status)
           if slot is not None and slot.status is not None else A.SLOT_PENDING),
    ]
    if slot is not None and slot.note:
        lines.append(f"{A.SLOT_NOTE}: {slot.note}")

    back_to_grid = common.button(
        A.BTN_BACK_TO_GRID, "attend", "course", course.id,
        grid.page_of(slots, session_date),
    )
    # A session whose date hasn't arrived yet can't be marked — no outcome
    # picker, just the info and a way back.
    if session_date > date.today():
        lines.append("")
        lines.append(A.ATTEND_FUTURE)
        common.render(req, "\n".join(lines), common.inline([[back_to_grid]]))
        return

    if staged_note:
        lines.append("")
        lines.append(A.SLOT_STAGED_NOTE.format(note=staged_note))
    lines.append("")
    lines.append(A.ASK_ATTEND_OUTCOME)

    token = grid.date_token(session_date)
    rows = [
        [_status_button(course.id, token, status) for status in grid.PRIMARY_STATUSES],
        [_status_button(course.id, token, status) for status in grid.SECONDARY_STATUSES],
        [common.button(A.BTN_ADD_NOTE, "attend", "note", course.id, token)],
        [back_to_grid],
    ]
    body = "\n".join(lines)
    if staged_note:
        # Keep the note in state so the next outcome tap saves it (and a further
        # text message just replaces it).
        common.prompt(
            req, body, _NOTE_STEP,
            {"course_id": course.id, "date": token, "note": staged_note},
            keyboard=common.inline(rows),
        )
    else:
        common.render(req, body, common.inline(rows))


def _status_button(course_id: int, token: str, status: AttendanceStatus) -> dict:
    return common.button(
        grid.PICKER_LABELS[status],
        "attend", "set", course_id, token, grid.CODE_BY_STATUS[status],
    )


def _set(req: AdminReq, rest: str) -> None:
    """Record (or correct) one session's outcome, then return to the grid."""
    course_id, _, tail = rest.partition(":")
    token, _, code = tail.partition(":")
    session_date = grid.parse_date_token(token)
    status = grid.STATUS_CODES.get(code)
    if not course_id.isdigit() or session_date is None or status is None:
        _pick_active(req)
        return
    if session_date > date.today():  # future session — a stale tap can't record it
        common.clear(req)
        _grid(req, int(course_id), page=None, flash=A.ATTEND_FUTURE)
        return

    note = _staged_note(req, int(course_id), token)
    try:
        attendance_service.record(
            req.db,
            int(course_id),
            session_date,
            status,
            note=note,
            created_by=req.user_id,
        )
        flash = A.ATTEND_SAVED
    except DomainError as exc:
        # e.g. the course is finished or out of paid sessions — say so on the
        # grid itself rather than replacing the screen with a bare error.
        flash = f"⚠️ {exc}"
    common.clear(req)
    _grid(req, int(course_id), page=None, flash=flash)


def _staged_note(req: AdminReq, course_id: int, token: str) -> str | None:
    """The note the admin typed before choosing an outcome, if any."""
    state = req.store.get(req.ctx.platform, req.chat_id)
    if state is None or state.step != _NOTE_STEP:
        return None
    data = state.data
    if data.get("course_id") != course_id or data.get("date") != token:
        return None
    return data.get("note")
