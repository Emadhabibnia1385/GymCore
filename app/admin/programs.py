"""Admin section: programs — send them to students, and manage their types.

«📄 مدیریت برنامه‌ها» opens a hub: send a program (pick a student, its type, an
optional note, then a PDF, photo or video), or edit the program-type catalog.
A student's own program list, reached from their profile, resends anything
already sent.
"""

from __future__ import annotations

from app.admin import common
from app.admin.common import AdminReq
from app.bots.common import formatting
from app.copy import admin_texts as A
from app.core.exceptions import DomainError
from app.models import Role, StudentType
from app.services import persons as persons_service
from app.services import plans as plans_service

_PER_PAGE = 10
_TYPE_ICONS = {StudentType.ONLINE: "🌐", StudentType.IN_PERSON: "🏋️"}


def handle_callback(req: AdminReq, args: str) -> None:
    action, _, rest = (args or "").partition(":")
    if action == "types":
        _types(req)
    elif action == "new_type":
        common.prompt(req, A.ASK_PLAN_TYPE_TITLE, "plans:new_type", {},
                      keyboard=common.cancel_keyboard(("plans", "types")))
    elif action == "toggle_type" and rest.isdigit():
        plan_type = plans_service.get_type(req.db, int(rest))
        plans_service.update_type(req.db, plan_type.id, active=not plan_type.active)
        _types(req)
    elif action == "edit_type" and rest.isdigit():
        plan_type = plans_service.get_type(req.db, int(rest))
        common.prompt(
            req, f"عنوان فعلی: {plan_type.title}\n\n{A.ASK_PLAN_TYPE_TITLE}",
            f"plans:edit_type:{plan_type.id}", {},
            keyboard=common.cancel_keyboard(("plans", "types")),
        )
    elif action == "del_type" and rest.isdigit():
        plan_type = plans_service.get_type(req.db, int(rest))
        common.render(
            req, A.PLAN_TYPE_DELETE_CONFIRM.format(title=plan_type.title),
            common.inline([[
                common.button(A.BTN_YES_DELETE, "plans", "delete_type", plan_type.id),
                common.button(A.CANCEL, "plans", "types"),
            ]]),
        )
    elif action == "delete_type" and rest.isdigit():
        try:
            plans_service.delete_type(req.db, int(rest))
        except DomainError as exc:
            _types(req, flash=f"⚠️ {exc}")
            return
        _types(req, flash=A.PLAN_TYPE_DELETED)
    elif action == "pick":
        _, _, page = rest.partition(":")  # "page:N"
        _pick_student(req, page=int(page) if page.isdigit() else 1)
    elif action == "client" and rest.isdigit():
        _client(req, int(rest))
    elif action == "assign" and rest.isdigit():
        _pick_type(req, int(rest))
    elif action == "new_type_for" and rest.isdigit():
        common.prompt(req, A.ASK_PLAN_TYPE_TITLE, "plans:new_type_for", {"client_id": int(rest)},
                      keyboard=common.cancel_keyboard(("plans", "assign", int(rest))))
    elif action == "resend" and rest.isdigit():
        _resend(req, int(rest))
    elif action == "type":
        client_id, _, type_id = rest.partition(":")
        if client_id.isdigit() and type_id.isdigit():
            _ask_note(req, {"client_id": int(client_id), "type_id": int(type_id)})
    elif action == "note_skip":
        _ask_file(req, _state_data(req))
    elif action == "file_skip":
        _assign(req, _state_data(req), None, None, None)
    else:
        _hub(req)


def handle_message(req: AdminReq, message: dict, substep: str, state) -> None:
    text = (message.get("text") or "").strip()
    data = state.data
    if substep == "new_type":
        plan_type = _create_type(req, text, "plans:new_type", {}, ("plans", "types"))
        if plan_type is not None:
            common.clear(req)
            _types(req, flash=A.PLAN_TYPE_SAVED)
    elif substep == "new_type_for":
        client_id = data.get("client_id")
        plan_type = _create_type(
            req, text, "plans:new_type_for", data, ("plans", "assign", client_id)
        )
        if plan_type is not None:
            _ask_note(req, {"client_id": client_id, "type_id": plan_type.id})
    elif substep.startswith("edit_type:"):
        _, _, id_str = substep.partition(":")
        if not text:
            common.prompt(req, A.ASK_PLAN_TYPE_TITLE, f"plans:{substep}", {},
                          keyboard=common.cancel_keyboard(("plans", "types")))
            return
        if id_str.isdigit():
            plans_service.update_type(req.db, int(id_str), title=text)
        common.clear(req)
        _types(req, flash=A.PLAN_TYPE_SAVED)
    elif substep == "find":
        _pick_student(req, query=text or None)
    elif substep in ("note", "text"):
        # Sending the file straight away (its caption as the note) skips a step.
        file_id, file_name, kind = _extract_file(message)
        if file_id is not None:
            data["note"] = (message.get("caption") or "").strip() or None
            _assign(req, data, file_id, file_name, kind)
            return
        data["note"] = text or None
        if substep == "text":  # the text IS the program
            _assign(req, data, None, None, None)
        else:
            _ask_file(req, data)
    elif substep == "file":
        file_id, file_name, kind = _extract_file(message)
        if file_id is None:  # text or a sticker where the file was expected
            _ask_file(req, data, warning=A.PLAN_FILE_EXPECTED)
            return
        caption = (message.get("caption") or "").strip()
        if caption and not data.get("note"):
            data["note"] = caption
        _assign(req, data, file_id, file_name, kind)
    else:
        common.clear(req)


def _extract_file(message: dict) -> tuple[str | None, str | None, str | None]:
    """The program file in a message as (file_id, file_name, kind), else Nones.

    An animation (GIF) arrives with a `document` as well, so it goes out as one.
    """
    document = message.get("document")
    if document:
        return document.get("file_id"), document.get("file_name"), "document"
    photos = message.get("photo")
    if photos:
        return photos[-1].get("file_id"), "photo.jpg", "photo"
    video = message.get("video")
    if video:
        return video.get("file_id"), video.get("file_name") or "video.mp4", "video"
    return None, None, None


def _state_data(req: AdminReq) -> dict:
    state = req.store.get(req.ctx.platform, req.chat_id)
    return state.data if state else {}


def _create_type(req: AdminReq, text: str, step: str, data: dict, cancel_parts: tuple):
    """Create a program type from typed text, re-asking on a blank or bad title."""
    if text:
        try:
            return plans_service.create_type(req.db, title=text)
        except DomainError as exc:
            warning = f"⚠️ {exc}\n"
    else:
        warning = ""
    common.prompt(req, f"{warning}{A.ASK_PLAN_TYPE_TITLE}", step, data,
                  keyboard=common.cancel_keyboard(cancel_parts))
    return None


def _ask_note(req: AdminReq, data: dict) -> None:
    common.prompt(req, A.ASK_PLAN_NOTE, "plans:note", data,
                  keyboard=common.skip_keyboard(("plans", "note_skip")))


def _ask_file(req: AdminReq, data: dict, warning: str | None = None) -> None:
    text = f"{warning}\n{A.ASK_PLAN_FILE}" if warning else A.ASK_PLAN_FILE
    common.prompt(req, text, "plans:file", data,
                  keyboard=common.skip_keyboard(("plans", "file_skip")))


def _assign(
    req: AdminReq,
    data: dict,
    file_id: str | None,
    file_name: str | None,
    file_kind: str | None,
) -> None:
    if "client_id" not in data or "type_id" not in data:
        _hub(req)
        return
    client_id = data["client_id"]
    if file_id is None and not data.get("note"):
        # Neither a file nor any text: the student would receive an empty program.
        common.prompt(req, A.PLAN_EMPTY, "plans:text", data,
                      keyboard=common.cancel_keyboard(("plans", "client", client_id)))
        return
    plans_service.create_assignment(
        req.db,
        person_id=client_id,
        plan_type_id=data["type_id"],
        coach_note=data.get("note"),
        original_filename=file_name,
        platform_file_id=file_id,
        file_platform=req.ctx.platform if file_id else None,
        file_kind=file_kind if file_id else None,
        created_by=req.user_id,
        notify=True,
    )
    person = persons_service.get(req.db, client_id)
    common.clear(req)
    rows = [
        [common.button(A.BTN_ANOTHER_PLAN, "plans", "assign", client_id)],
        [common.button(A.PROGRAMS_OF.format(name=person.name), "plans", "client", client_id)],
    ]
    common.render(req, A.PLAN_ASSIGNED, common.with_back(rows))


def _hub(req: AdminReq) -> None:
    rows = [
        [common.button(A.BTN_ASSIGN_PLAN, "plans", "pick")],
        [common.button(A.BTN_PLAN_TYPES, "plans", "types")],
    ]
    common.render(req, f"{A.PROGRAMS_TITLE}\n{A.PROGRAMS_HUB_HINT}", common.with_back(rows))


def _types(req: AdminReq, flash: str | None = None) -> None:
    types = plans_service.list_types(req.db)
    rows = [[common.button(A.BTN_NEW_PLAN_TYPE, "plans", "new_type")]]
    for t in types:
        rows.append([
            common.button(f"{'🟢' if t.active else '⚪'} {t.title}", "plans", "toggle_type", t.id),
            common.button("✏️", "plans", "edit_type", t.id),
            common.button("🗑", "plans", "del_type", t.id),
        ])
    body = f"{A.PLAN_TYPES_TITLE}\n{A.PROGRAMS_HINT}"
    common.render(req, f"{flash}\n\n{body}" if flash else body, common.with_back(rows, ("plans",)))


def _pick_student(req: AdminReq, page: int = 1, query: str | None = None) -> None:
    """Every student to send a program to — online ones first, since programs
    are what they train with. Typing a name narrows the list."""
    stmt = persons_service.search_stmt(Role.CLIENT, query, None)
    people = sorted(
        req.db.scalars(stmt), key=lambda p: (p.student_type != StudentType.ONLINE, p.name)
    )
    if query:
        people, pages = people[:_PER_PAGE], 1
        text = A.PICK_STUDENT_RESULTS.format(query=query) if people else A.PICK_STUDENT_NONE
    else:
        pages = max((len(people) + _PER_PAGE - 1) // _PER_PAGE, 1)
        page = max(min(page, pages), 1)
        people = people[(page - 1) * _PER_PAGE: page * _PER_PAGE]
        text = A.ASK_PICK_STUDENT
    rows = [
        [common.button(f"{_TYPE_ICONS.get(p.student_type, '')} {p.name}", "plans", "assign", p.id)]
        for p in people
    ]
    keyboard = common.pager(rows, page, pages, ("plans", "pick"), ("plans",))
    common.prompt_show(req, text, "plans:find", {}, keyboard)


def _client(req: AdminReq, client_id: int) -> None:
    person = persons_service.get(req.db, client_id)
    assignments = plans_service.list_assignments(req.db, person_id=client_id)
    rows = [[common.button(A.BTN_ASSIGN_PLAN, "plans", "assign", client_id)]]
    for assignment in assignments[:10]:
        rows.append([common.button(
            f"🔁 {formatting.program_label(assignment)}", "plans", "resend", assignment.id
        )])
    hint = A.PROGRAMS_RESEND_HINT if assignments else A.NO_PROGRAMS_YET
    common.render(
        req, f"{A.PROGRAMS_OF.format(name=person.name)}\n{hint}",
        common.with_back(rows, ("students", "view", client_id)),
    )


def _resend(req: AdminReq, assignment_id: int) -> None:
    """Re-deliver an existing program to the client on each linked platform."""
    from app.bots.common import client_flow
    from app.bots.common.client import build_client
    from app.bots.common.context import make_context

    assignment = plans_service.get_assignment(req.db, assignment_id)
    caption = formatting.format_program_caption(assignment)
    for identity in assignment.person.identities:
        client = build_client(identity.platform)
        if client is None:
            continue
        try:
            ctx = make_context(client)
            client_flow._deliver_program(ctx, assignment, identity.platform_user_id, caption)
        finally:
            client.close()
    common.render(req, A.PLAN_RESENT, common.back_home("plans", "client", assignment.person_id))


def _pick_type(req: AdminReq, client_id: int) -> None:
    person = persons_service.get(req.db, client_id)
    types = plans_service.list_types(req.db, only_active=True)
    rows = [[common.button(t.title, "plans", "type", client_id, t.id)] for t in types]
    rows.append([common.button(A.BTN_NEW_PLAN_TYPE, "plans", "new_type_for", client_id)])
    common.render(
        req, A.ASK_PLAN_TYPE_FOR.format(name=person.name),
        common.with_back(rows, ("plans", "client", client_id)),
    )
