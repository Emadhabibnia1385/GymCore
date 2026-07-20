"""Admin section: program catalog (PlanType) + assigning programs to clients."""

from __future__ import annotations

from app.admin import common
from app.admin.common import AdminReq
from app.copy import admin_texts as A
from app.core.exceptions import DomainError
from app.core.jalali import format_jalali
from app.services import persons as persons_service
from app.services import plans as plans_service


def handle_callback(req: AdminReq, args: str) -> None:
    action, _, rest = (args or "").partition(":")
    if action == "new_type":
        common.prompt(req, A.ASK_PLAN_TYPE_TITLE, "plans:new_type", {})
    elif action == "toggle_type" and rest.isdigit():
        plan_type = plans_service.get_type(req.db, int(rest))
        plans_service.update_type(req.db, plan_type.id, active=not plan_type.active)
        _types(req)
    elif action == "edit_type" and rest.isdigit():
        plan_type = plans_service.get_type(req.db, int(rest))
        common.prompt(
            req, f"عنوان فعلی: {plan_type.title}\n\n{A.ASK_PLAN_TYPE_TITLE}",
            f"plans:edit_type:{plan_type.id}", {},
        )
    elif action == "delete_type" and rest.isdigit():
        try:
            plans_service.delete_type(req.db, int(rest))
        except DomainError as exc:
            common.send(req, str(exc))
        _types(req)
    elif action == "client" and rest.isdigit():
        _client(req, int(rest))
    elif action == "assign" and rest.isdigit():
        _pick_type(req, int(rest))
    elif action == "resend" and rest.isdigit():
        _resend(req, int(rest))
    elif action == "type":
        client_id, _, type_id = rest.partition(":")
        if client_id.isdigit() and type_id.isdigit():
            common.prompt(
                req, A.ASK_PLAN_NOTE, "plans:note",
                {"client_id": int(client_id), "type_id": int(type_id)},
                keyboard=common.skip_keyboard(("plans", "note_skip")),
            )
    elif action == "note_skip":
        state = req.store.get(req.ctx.platform, req.chat_id)
        data = state.data if state else {}
        common.prompt(req, A.ASK_PLAN_FILE, "plans:file", data,
                      keyboard=common.skip_keyboard(("plans", "file_skip")))
    elif action == "file_skip":
        _assign(req, file_id=None, file_name=None)
    else:
        _types(req)


def handle_message(req: AdminReq, message: dict, substep: str, state) -> None:
    text = (message.get("text") or "").strip()
    data = state.data
    if substep == "new_type":
        if not text:
            common.prompt(req, A.ASK_PLAN_TYPE_TITLE, "plans:new_type", {})
            return
        plans_service.create_type(req.db, title=text)
        common.clear(req)
        _types(req)
    elif substep.startswith("edit_type:"):
        _, _, id_str = substep.partition(":")
        if not text:
            common.prompt(req, A.ASK_PLAN_TYPE_TITLE, substep, {})
            return
        if id_str.isdigit():
            plans_service.update_type(req.db, int(id_str), title=text)
        common.clear(req)
        _types(req)
    elif substep == "note":
        data["note"] = text or None
        common.prompt(req, A.ASK_PLAN_FILE, "plans:file", data,
                      keyboard=common.skip_keyboard(("plans", "file_skip")))
    elif substep == "file":
        file_id, file_name = _extract_file(message)
        _assign(req, file_id=file_id, file_name=file_name)
    else:
        common.clear(req)


def _extract_file(message: dict) -> tuple[str | None, str | None]:
    document = message.get("document")
    if document:
        return document.get("file_id"), document.get("file_name")
    photos = message.get("photo")
    if photos:
        return photos[-1].get("file_id"), "photo.jpg"
    return None, None


def _assign(req: AdminReq, file_id: str | None, file_name: str | None) -> None:
    state = req.store.get(req.ctx.platform, req.chat_id)
    if state is None or "client_id" not in state.data or "type_id" not in state.data:
        _types(req)
        return
    data = state.data
    plans_service.create_assignment(
        req.db,
        person_id=data["client_id"],
        plan_type_id=data["type_id"],
        coach_note=data.get("note"),
        original_filename=file_name,
        platform_file_id=file_id,
        file_platform=req.ctx.platform if file_id else None,
        created_by=req.user_id,
        notify=True,
    )
    client_id = data["client_id"]
    common.clear(req)
    common.render(req, A.PLAN_ASSIGNED, common.back_home("plans", "client", client_id))


def _types(req: AdminReq) -> None:
    types = plans_service.list_types(req.db)
    rows = [[common.button(A.BTN_NEW_PLAN_TYPE, "plans", "new_type")]]
    for t in types:
        rows.append([
            common.button(f"{'🟢' if t.active else '⚪'} {t.title}", "plans", "toggle_type", t.id),
            common.button("✏️", "plans", "edit_type", t.id),
            common.button("🗑", "plans", "delete_type", t.id),
        ])
    common.render(req, f"{A.PROGRAMS_TITLE}\n{A.PROGRAMS_HINT}", common.with_back(rows))


def _client(req: AdminReq, client_id: int) -> None:
    persons_service.get(req.db, client_id)
    assignments = plans_service.list_assignments(req.db, person_id=client_id)
    rows = [[common.button(A.BTN_ASSIGN_PLAN, "plans", "assign", client_id)]]
    for assignment in assignments[:10]:
        label = (
            f"{A.BTN_RESEND}  {assignment.plan_type.title} "
            f"| {format_jalali(assignment.created_at)}"
        )
        rows.append([common.button(label, "plans", "resend", assignment.id)])
    body = A.PROGRAMS_TITLE if assignments else f"{A.PROGRAMS_TITLE}\n{A.NOTHING}"
    common.render(req, body, common.with_back(rows, ("students", "view", client_id)))


def _resend(req: AdminReq, assignment_id: int) -> None:
    """Re-deliver an existing program to the client on each linked platform."""
    from app.bots.common import client_flow, formatting
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
    types = plans_service.list_types(req.db, only_active=True)
    rows = [[common.button(t.title, "plans", "type", client_id, t.id)] for t in types]
    common.render(req, A.ASK_PLAN_TYPE, common.with_back(rows, ("plans", "client", client_id)))
