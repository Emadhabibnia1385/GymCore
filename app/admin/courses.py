"""Admin section: course management (create, view, status, renew)."""

from __future__ import annotations

from app.admin import common
from app.admin.common import AdminReq
from app.bots.common import formatting
from app.copy import admin_texts as A
from app.models import CourseStatus
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import persons as persons_service


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
        course = courses_service.create(
            req.db,
            client_id=data["client_id"],
            class_type_id=data["class_type_id"],
            sessions_total=data["sessions_total"],
            tuition=data["tuition"],
            gym_fee=data["gym_fee"],
            allowed_absence=data["allowed_absence"],
            start_date=start,
        )
        common.clear(req)
        common.send(req, A.COURSE_CREATED)
        _view(req, course.id)
    elif substep == "renew":
        count = common.parse_count(text)
        if not count:
            common.prompt(req, f"{A.INVALID_NUMBER}\n{A.ASK_RENEW_SESSIONS}", "courses:renew", data)
            return
        new_course = courses_service.renew(req.db, data["course_id"], sessions_total=count)
        common.clear(req)
        common.send(req, A.RENEWED)
        _view(req, new_course.id)
    else:
        common.clear(req)


def _list_for_client(req: AdminReq, client_id: int) -> None:
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
    common.render(req, A.COURSES_TITLE, common.with_back(rows, ("students", "view", client_id)))


def _pick_class(req: AdminReq, client_id: int) -> None:
    types = classes_service.list_class_types(req.db, only_active=True)
    rows = [[common.button(c.title, "courses", "cls", client_id, c.id)] for c in types]
    common.render(req, A.ASK_COURSE_CLASS, common.with_back(rows, ("courses", "client", client_id)))


def _view(req: AdminReq, course_id: int) -> None:
    course = courses_service.get(req.db, course_id)
    body = formatting.format_course_detail(req.db, course)
    rows: list[list[dict]] = []
    if course.status == CourseStatus.ACTIVE:
        rows.append([
            common.button(A.BTN_PAUSE_COURSE, "courses", "status", course.id, "PAUSED"),
            common.button(A.BTN_FINISH_COURSE, "courses", "status", course.id, "FINISHED"),
        ])
    elif course.status == CourseStatus.PAUSED:
        rows.append([
            common.button(A.BTN_RESUME_COURSE, "courses", "status", course.id, "ACTIVE"),
            common.button(A.BTN_FINISH_COURSE, "courses", "status", course.id, "FINISHED"),
        ])
    rows.append([common.button(A.BTN_RENEW_COURSE, "courses", "renew", course.id)])
    rows.append([
        common.button(A.BTN_ATTENDANCE, "attend", "course", course.id),
        common.button(A.BTN_PAYMENTS, "pay", "course", course.id),
    ])
    common.render(req, body, common.with_back(rows, ("courses", "client", course.client_id)))
