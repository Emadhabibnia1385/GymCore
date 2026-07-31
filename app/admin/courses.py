"""Admin section: course management (create, view, status, renew)."""

from __future__ import annotations

from datetime import date

from app.admin import common
from app.admin.common import AdminReq
from app.bots.common import formatting
from app.copy import admin_texts as A
from app.models import CourseStatus
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import persons as persons_service
from app.services import schedule as schedule_service


def handle_callback(req: AdminReq, args: str) -> None:
    action, _, rest = (args or "").partition(":")
    if action == "client" and rest.isdigit():
        _list_for_client(req, int(rest))
    elif action == "view" and rest.isdigit():
        _view(req, int(rest))
    elif action == "new" and rest.isdigit():
        _pick_class(req, int(rest))
    elif action == "cls":
        client_id, _, class_type_id = rest.partition(":")
        if client_id.isdigit() and class_type_id.isdigit():
            common.prompt(
                req, A.ASK_COURSE_SESSIONS, "courses:sessions",
                {"client_id": int(client_id), "class_type_id": int(class_type_id)},
            )
    elif action == "status":
        course_id, _, status = rest.partition(":")
        if course_id.isdigit() and status in CourseStatus.__members__:
            courses_service.set_status(req.db, int(course_id), CourseStatus[status])
            _view(req, int(course_id))
    elif action == "renew" and rest.isdigit():
        common.prompt(req, A.ASK_RENEW_SESSIONS, "courses:renew", {"course_id": int(rest)})
    elif action == "del_confirm" and rest.isdigit():
        course = courses_service.get(req.db, int(rest))
        common.render(
            req,
            A.CONFIRM_DELETE_COURSE.format(title=course.class_type.title),
            common.inline([[
                common.button(A.BTN_YES_DELETE, "courses", "del", course.id),
                common.button(A.CANCEL, "courses", "view", course.id),
            ]]),
        )
    elif action == "del" and rest.isdigit():
        client_id = courses_service.delete(req.db, int(rest))
        _list_for_client(req, client_id, flash=A.COURSE_DELETED)
    elif action == "time_skip":
        state = req.store.get(req.ctx.platform, req.chat_id)
        data = state.data if state else {}
        data["class_time"] = None
        if data.get("start_date"):
            start = date.fromisoformat(data["start_date"])
            data["days"] = [schedule_service.persian_weekday(start)]
        _ask_weekdays(req, data)
    elif action == "wd" and rest.isdigit():
        _toggle_weekday(req, int(rest))
    elif action == "wd_done":
        _finish_weekdays(req)
    elif action == "wdedit" and rest.isdigit():
        course = courses_service.get(req.db, int(rest))
        _ask_weekdays(
            req,
            {"course_id": course.id, "days": schedule_service.parse_weekdays(course.weekdays)},
        )
    else:
        common.render(req, A.COURSES_TITLE, common.with_back([]))


def handle_message(req: AdminReq, message: dict, substep: str, state) -> None:
    text = (message.get("text") or "").strip()
    data = state.data
    if substep == "sessions":
        count = common.parse_count(text)
        if not count:
            common.prompt(
                req, f"{A.INVALID_NUMBER}\n{A.ASK_COURSE_SESSIONS}", "courses:sessions", data
            )
            return
        data["sessions_total"] = count
        common.prompt(req, A.ASK_COURSE_TUITION, "courses:tuition", data)
    elif substep == "tuition":
        amount = common.parse_count(text)
        if amount is None:
            common.prompt(
                req, f"{A.INVALID_NUMBER}\n{A.ASK_COURSE_TUITION}", "courses:tuition", data
            )
            return
        data["tuition"] = amount
        common.prompt(req, A.ASK_COURSE_GYM_FEE, "courses:gym_fee", data)
    elif substep == "gym_fee":
        amount = common.parse_count(text)
        if amount is None:
            common.prompt(
                req, f"{A.INVALID_NUMBER}\n{A.ASK_COURSE_GYM_FEE}", "courses:gym_fee", data
            )
            return
        data["gym_fee"] = amount
        common.prompt(req, A.ASK_COURSE_ALLOWED, "courses:allowed", data)
    elif substep == "allowed":
        count = common.parse_count(text)
        if count is None:
            common.prompt(
                req, f"{A.INVALID_NUMBER}\n{A.ASK_COURSE_ALLOWED}", "courses:allowed", data
            )
            return
        data["allowed_absence"] = count
        common.prompt(req, A.ASK_COURSE_START, "courses:start", data)
    elif substep == "start":
        start = common.parse_date(text)
        if start is None:
            common.prompt(req, A.INVALID_DATE, "courses:start", data)
            return
        data["start_date"] = start.isoformat()
        common.prompt(req, A.ASK_COURSE_TIME, "courses:time", data,
                      keyboard=common.skip_keyboard(("courses", "time_skip")))
    elif substep == "time":
        data["class_time"] = text or None
        # Then the weekly pattern (session grid), pre-selected with the start weekday.
        data["days"] = [schedule_service.persian_weekday(date.fromisoformat(data["start_date"]))]
        _ask_weekdays(req, data)
    elif substep == "renew":
        count = common.parse_count(text)
        if not count:
            common.prompt(req, f"{A.INVALID_NUMBER}\n{A.ASK_RENEW_SESSIONS}", "courses:renew", data)
            return
        new_course = courses_service.renew(req.db, data["course_id"], sessions_total=count)
        common.clear(req)
        _view(req, new_course.id, flash=A.RENEWED)
    elif substep == "weekdays":
        _ask_weekdays(req, data)  # stray text mid-selection: just re-show the picker
    else:
        common.clear(req)


# --- weekly training pattern (drives the session grid) ---

_WEEKDAY_STEP = "courses:weekdays"


def _ask_weekdays(req: AdminReq, data: dict) -> None:
    """Multi-select day picker; taps re-render in place until «تأیید»."""
    selected = set(data.get("days") or [])
    cells = [
        common.button(
            f"{'🟢' if index in selected else '⚪'} {name}", "courses", "wd", index
        )
        for index, name in enumerate(schedule_service.WEEKDAY_NAMES)
    ]
    rows = [cells[:4], cells[4:], [common.button(A.BTN_WEEKDAYS_DONE, "courses", "wd_done")]]
    body = (
        f"{A.ASK_COURSE_WEEKDAYS}\n\n"
        f"🗓 {schedule_service.weekdays_label(schedule_service.format_weekdays(selected))}"
    )
    common.prompt_show(req, body, _WEEKDAY_STEP, data, keyboard=common.inline(rows))


def _toggle_weekday(req: AdminReq, index: int) -> None:
    state = req.store.get(req.ctx.platform, req.chat_id)
    if state is None or state.step != _WEEKDAY_STEP:
        common.render(req, A.COURSES_TITLE, common.with_back([]))
        return
    days = set(state.data.get("days") or [])
    days.symmetric_difference_update({index})
    state.data["days"] = sorted(days)
    _ask_weekdays(req, state.data)


def _finish_weekdays(req: AdminReq) -> None:
    """«تأیید» — create the pending course, or save the edited pattern."""
    state = req.store.get(req.ctx.platform, req.chat_id)
    if state is None or state.step != _WEEKDAY_STEP:
        common.render(req, A.COURSES_TITLE, common.with_back([]))
        return
    data = state.data
    if not data.get("days"):
        common.send(req, A.NO_WEEKDAYS)
        _ask_weekdays(req, data)
        return
    weekdays = schedule_service.format_weekdays(data["days"])

    if "course_id" in data:  # editing an existing course
        course_id = data["course_id"]
        courses_service.set_weekdays(req.db, course_id, weekdays)
        common.clear(req)
        _view(req, course_id)
        return

    course = courses_service.create(
        req.db,
        client_id=data["client_id"],
        class_type_id=data["class_type_id"],
        sessions_total=data["sessions_total"],
        tuition=data["tuition"],
        gym_fee=data["gym_fee"],
        allowed_absence=data["allowed_absence"],
        start_date=date.fromisoformat(data["start_date"]),
        weekdays=weekdays,
        class_time=data.get("class_time"),
    )
    common.clear(req)
    _view(req, course.id, flash=A.COURSE_CREATED)


def _list_for_client(req: AdminReq, client_id: int, flash: str | None = None) -> None:
    persons_service.get(req.db, client_id)
    items = courses_service.list_courses(req.db, client_id=client_id)
    rows = [
        [common.button(
            f"{formatting.course_status_label(c.status)} {c.class_type.title} "
            f"| {courses_service.remaining_sessions(req.db, c)}",
            "courses", "view", c.id,
        )]
        for c in items
    ]
    rows.insert(0, [common.button(A.BTN_NEW_COURSE, "courses", "new", client_id)])
    body = f"{flash}\n\n{A.COURSES_TITLE}" if flash else A.COURSES_TITLE
    common.render(req, body, common.with_back(rows, ("students", "view", client_id)))


def _pick_class(req: AdminReq, client_id: int) -> None:
    types = classes_service.list_class_types(req.db, only_active=True)
    rows = [[common.button(c.title, "courses", "cls", client_id, c.id)] for c in types]
    common.render(req, A.ASK_COURSE_CLASS, common.with_back(rows, ("courses", "client", client_id)))


def _view(req: AdminReq, course_id: int, flash: str | None = None) -> None:
    course = courses_service.get(req.db, course_id)
    # Admin has the full session grid one tap away, so the per-date history list
    # is left out here to keep the course card compact.
    body = formatting.format_course_detail(req.db, course, show_history=False)
    if flash:
        body = f"{flash}\n\n{body}"
    rows: list[list[dict]] = [[
        common.button(A.BTN_STUDENT_GRID, "attend", "course", course.id),
        common.button(A.BTN_EDIT_WEEKDAYS, "courses", "wdedit", course.id),
    ]]
    rows.append([
        common.button(A.BTN_RENEW_COURSE, "courses", "renew", course.id),
        common.button(A.BTN_PAYMENTS, "pay", "course", course.id),
    ])
    rows.append([common.button(A.BTN_DELETE_COURSE, "courses", "del_confirm", course.id)])
    common.render(req, body, common.with_back(rows, ("courses", "client", course.client_id)))
