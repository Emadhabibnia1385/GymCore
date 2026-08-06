"""Admin section: student management (search, create, profile, pause/activate)."""

from __future__ import annotations

from app.admin import common
from app.admin.common import AdminReq
from app.copy import admin_texts as A
from app.copy import texts
from app.core.exceptions import ConflictError, ValidationError
from app.models import Role
from app.services import courses as courses_service
from app.services import notifications as notify_service
from app.services import persons as persons_service
from app.services import schedule as schedule_service

_EDIT_FIELDS = ("edit_name", "edit_phone", "edit_phone2")
_EDIT_PROMPTS = {
    "edit_name": A.ASK_EDIT_NAME,
    "edit_phone": A.ASK_EDIT_PHONE,
    "edit_phone2": A.ASK_EDIT_PHONE2,
}

_PER_PAGE = 6
_PLATFORM_LABELS = {"TELEGRAM": "تلگرام", "BALE": "بله"}


def handle_callback(req: AdminReq, args: str) -> None:
    action, _, rest = (args or "").partition(":")
    if action in ("", "list"):
        _list(req, page=1)
    elif action == "page":
        _list(req, page=common.parse_count(rest) or 1)
    elif action == "view" and rest.isdigit():
        _profile(req, int(rest))
    elif action == "new":
        common.prompt(req, A.ASK_STUDENT_NAME, "students:new_name", {})
    elif action == "search":
        common.prompt(req, A.STUDENTS_HINT, "students:search", {})
    elif action == "new_phone_skip":
        state = req.store.get(req.ctx.platform, req.chat_id)
        _create(req, (state.data.get("name") if state else None), None)
    elif action == "del_confirm" and rest.isdigit():
        person = persons_service.get(req.db, int(rest))
        common.render(
            req,
            A.CONFIRM_DELETE_STUDENT.format(name=person.name),
            common.inline([[
                common.button(A.BTN_YES_DELETE, "students", "del", person.id),
                common.button(A.CANCEL, "students", "view", person.id),
            ]]),
        )
    elif action == "msg" and rest.isdigit():
        person = persons_service.get(req.db, int(rest))
        if not person.identities:
            common.send(req, A.STUDENT_NO_ACCOUNT)
            _profile(req, person.id)
        else:
            common.prompt(req, A.ASK_STUDENT_MESSAGE, f"students:msg:{person.id}", {})
    elif action == "edit" and rest.isdigit():
        _edit_menu(req, int(rest))
    elif action in _EDIT_FIELDS and rest.isdigit():
        common.prompt(req, _EDIT_PROMPTS[action], f"students:{action}", {"id": int(rest)})
    elif action == "del" and rest.isdigit():
        persons_service.delete(req.db, int(rest))
        _list(req)
    else:
        _list(req)


def handle_message(req: AdminReq, message: dict, substep: str, state) -> None:
    text = (message.get("text") or "").strip()
    if substep == "new_name":
        if not text:
            common.prompt(req, A.ASK_STUDENT_NAME, "students:new_name", {})
            return
        common.prompt(
            req, A.ASK_STUDENT_PHONE, "students:new_phone", {"name": text},
            keyboard=common.skip_keyboard(("students", "new_phone_skip")),
        )
    elif substep == "new_phone":
        _create(req, state.data.get("name"), text or None)
    elif substep == "search":
        _list(req, page=1, query=text)
    elif substep.startswith("msg:"):
        _, _, id_str = substep.partition(":")
        if not id_str.isdigit():
            common.clear(req)
            _list(req)
            return
        if text:
            person = persons_service.get(req.db, int(id_str))
            notify_service.notify_person(req.db, person, f"💬 پیام از مربی:\n{text}")
            common.send(req, A.MESSAGE_SENT)
        common.clear(req)
        _profile(req, int(id_str))
    elif substep in _EDIT_FIELDS:
        _apply_edit(req, substep, state.data.get("id"), text)
    else:
        common.clear(req)
        _list(req)


def _create(req: AdminReq, name: str | None, phone: str | None) -> None:
    if not name:
        common.render(req, A.CANCELLED)
        return
    person = persons_service.create(req.db, name=name, phone=phone, role=Role.CLIENT)
    common.clear(req)
    _profile(req, person.id)


def _edit_menu(req: AdminReq, person_id: int) -> None:
    """Pick which field of a student to edit."""
    person = persons_service.get(req.db, person_id)
    body = (
        f"{A.EDIT_STUDENT_TITLE}\n\n"
        f"👤 {person.name}\n"
        f"{A.LABEL_PHONE}: {person.phone or '-'}\n"
        f"{A.LABEL_PHONE2}: {person.phone2 or '-'}"
    )
    rows = [
        [common.button(A.BTN_EDIT_NAME, "students", "edit_name", person.id)],
        [
            common.button(A.BTN_EDIT_PHONE, "students", "edit_phone", person.id),
            common.button(A.BTN_EDIT_PHONE2, "students", "edit_phone2", person.id),
        ],
    ]
    common.render(req, body, common.with_back(rows, ("students", "view", person.id)))


def _apply_edit(req: AdminReq, field: str, person_id: int | None, text: str) -> None:
    if not person_id:
        common.clear(req)
        _list(req)
        return
    value = "" if text == A.CLEAR_WORD else text
    try:
        if field == "edit_name":
            if not value:
                common.prompt(req, A.ASK_EDIT_NAME, "students:edit_name", {"id": person_id})
                return
            persons_service.update(req.db, person_id, name=value)
        elif field == "edit_phone":
            persons_service.update(req.db, person_id, phone=value)
        else:  # edit_phone2
            persons_service.update(req.db, person_id, phone2=value)
    except (ValidationError, ConflictError) as exc:
        common.prompt(
            req, f"⚠️ {exc}\n{_EDIT_PROMPTS[field]}", f"students:{field}", {"id": person_id}
        )
        return
    common.clear(req)
    _profile(req, person_id)


def _list(req: AdminReq, page: int = 1, query: str | None = None) -> None:
    clients = list(req.db.scalars(persons_service.search_stmt(Role.CLIENT, query)))
    # Each student carries their active course's remaining sessions; the list is
    # sorted by that ascending (fewest first) so who needs a renewal is on top.
    enriched = []
    for person in clients:
        active = courses_service.active_course(req.db, person.id)
        remaining = courses_service.remaining_sessions(req.db, active) if active else None
        enriched.append((person, remaining))
    enriched.sort(key=lambda pr: (pr[1] is None, pr[1] if pr[1] is not None else 0))

    pages = max((len(enriched) + _PER_PAGE - 1) // _PER_PAGE, 1)
    page = max(min(page, pages), 1)
    window = enriched[(page - 1) * _PER_PAGE: page * _PER_PAGE]

    top = [[
        common.button(A.BTN_NEW_STUDENT, "students", "new"),
        common.button(A.BTN_SEARCH, "students", "search"),
    ]]
    item_rows = []
    for person, remaining in window:
        sessions = f"{remaining} جلسه" if remaining is not None else "بدون دوره"
        item_rows.append([
            common.button(person.name, "students", "view", person.id),
            common.button(sessions, "students", "view", person.id),
        ])
    if enriched:
        body = f"{A.STUDENTS_TITLE}\n{A.STUDENTS_HINT}"
    else:
        body = f"{A.STUDENTS_TITLE}\n\n{A.NO_STUDENTS if not query else A.NOTHING}"
    keyboard = common.pager(top + item_rows, page, pages, ("students",))
    common.render(req, body, keyboard)


def _profile(req: AdminReq, person_id: int) -> None:
    """That student's own menu — the hub every per-student action hangs off.

    The primary action is always on top: the session grid when the student has
    an active course, otherwise «دوره جدید» to give them one.
    """
    person = persons_service.get(req.db, person_id)
    active = courses_service.active_course(req.db, person.id)

    lines = [
        f"👤 {person.name}",
        f"{A.LABEL_PHONE}: {person.phone or '-'}",
    ]
    if person.phone2:
        lines.append(f"{A.LABEL_PHONE2}: {person.phone2}")
    platforms = sorted({identity.platform.value for identity in person.identities})
    if platforms:
        linked = "، ".join(_PLATFORM_LABELS.get(p, p) for p in platforms)
        lines.append(f"{A.LABEL_LINKED}: {linked}")
    lines.append("")
    if active is not None:
        consumed = courses_service.consumed_sessions(req.db, active.id)
        lines.append(f"📚 {A.LABEL_ACTIVE_COURSE}: {active.class_type.title}")
        lines.append(f"🎟 {A.LABEL_SESSIONS}: {consumed}/{active.sessions_total}")
        lines.append(
            f"🗓 {texts.LABEL_TRAINING_DAYS}: {schedule_service.class_schedule_label(active)}"
        )
    else:
        lines.append(f"📚 {A.NO_ACTIVE_COURSE}")
    lines.append("")
    lines.append(A.STUDENT_MENU_HINT)

    rows: list[list[dict]] = []
    if active is not None:
        rows.append([common.button(A.BTN_STUDENT_GRID, "attend", "course", active.id)])
    else:
        rows.append([common.button(A.BTN_NEW_COURSE_FOR, "courses", "new", person.id)])
    rows.append([
        common.button(A.BTN_COURSES, "courses", "client", person.id),
        common.button(A.BTN_PROGRAMS, "plans", "client", person.id),
    ])
    rows.append([
        common.button(A.BTN_PAYMENTS, "pay", "client", person.id),
        common.button(A.BTN_SEND_MESSAGE, "students", "msg", person.id),
    ])
    rows.append([
        common.button(A.BTN_EDIT_STUDENT, "students", "edit", person.id),
        common.button(A.BTN_DELETE_STUDENT, "students", "del_confirm", person.id),
    ])
    rows.append([common.button(A.BACK, "students")])
    common.render(req, "\n".join(lines), common.inline(rows))
