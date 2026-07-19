"""Admin section: student management (search, create, profile, pause/activate)."""

from __future__ import annotations

from app.admin import common
from app.admin.common import AdminReq
from app.copy import admin_texts as A
from app.models import Role
from app.repositories.pagination import paginate
from app.services import persons as persons_service

_PER_PAGE = 6


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
    elif action == "pause" and rest.isdigit():
        persons_service.set_active(req.db, int(rest), False)
        _profile(req, int(rest))
    elif action == "activate" and rest.isdigit():
        persons_service.set_active(req.db, int(rest), True)
        _profile(req, int(rest))
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


def _list(req: AdminReq, page: int = 1, query: str | None = None) -> None:
    stmt = persons_service.search_stmt(Role.CLIENT, query)
    result = paginate(req.db, stmt, page=page, per_page=_PER_PAGE)
    top = [[
        common.button(A.BTN_NEW_STUDENT, "students", "new"),
        common.button(A.BTN_SEARCH, "students", "search"),
    ]]
    item_rows = [
        [common.button(f"{'' if p.is_active else '⏸ '}{p.name}", "students", "view", p.id)]
        for p in result.items
    ]
    if result.items:
        body = f"{A.STUDENTS_TITLE}\n{A.STUDENTS_HINT}"
    else:
        body = f"{A.STUDENTS_TITLE}\n\n{A.NO_STUDENTS if not query else A.NOTHING}"
    keyboard = common.pager(top + item_rows, result.page, result.pages, ("students",))
    common.render(req, body, keyboard)


def _profile(req: AdminReq, person_id: int) -> None:
    person = persons_service.get(req.db, person_id)
    status = f"🟢 {A.LABEL_ACTIVE}" if person.is_active else f"⏸ {A.LABEL_INACTIVE}"
    body = (
        f"👤 {person.name}\n"
        f"{A.LABEL_PHONE}: {person.phone or '-'}\n"
        f"{A.LABEL_STATUS}: {status}"
    )
    toggle = (
        common.button(A.BTN_PAUSE, "students", "pause", person.id)
        if person.is_active
        else common.button(A.BTN_ACTIVATE, "students", "activate", person.id)
    )
    rows = [
        [common.button(A.BTN_COURSES, "courses", "client", person.id),
         common.button(A.BTN_PROGRAMS, "plans", "client", person.id)],
        [common.button(A.BTN_ATTENDANCE, "attend", "client", person.id),
         common.button(A.BTN_PAYMENTS, "pay", "client", person.id)],
        [toggle],
        [common.button(A.BACK, "students")],
    ]
    common.render(req, body, common.inline(rows))
