"""Admin section: «📦 پکیج‌ها» — program bundles built once, sent to many.

Reached from «📄 مدیریت برنامه‌ها». A package holds files (PDF, photo, video)
and text in order. The coach sends it to any number of students from a
multi-select picker, or to one student from that student's programs screen.
What a student sees is live, so an item added later reaches everyone who has
the package.

A file reaches the students of the platform it was sent from: each item keeps
one file_id per platform, and «📲 نسخهٔ …» explains how to send the same file
from the other bot (where that same button records it).

Callbacks are ``a:pkg:<action>:<args>`` — short, under the 64-byte cap.
"""

from __future__ import annotations

from app.admin import common
from app.admin import programs as programs_admin
from app.admin.common import AdminReq
from app.copy import admin_texts as A
from app.copy import packages_texts as P
from app.core.exceptions import NotFoundError, ValidationError
from app.models import Platform, Role, StudentType
from app.services import packages as packages_service
from app.services import persons as persons_service

S = "pkg"  # this section's key in panel.SECTIONS
_PER_PAGE = 10
_PICK_PER_PAGE = 8
_SEND_STEP = f"{S}:send"
_DESCRIPTION_EXCERPT = 400
_TEXT_EXCERPT = 600
_BOT_PLATFORMS = (Platform.TELEGRAM, Platform.BALE)


def handle_callback(req: AdminReq, args: str) -> None:
    action, _, rest = (args or "").partition(":")
    try:
        _on_callback(req, action, rest.split(":") if rest else [])
    except NotFoundError as exc:
        # An old button whose package, item or student is gone: back to the list.
        _list(req, flash=f"⚠️ {exc}")


def handle_message(req: AdminReq, message: dict, substep: str, state) -> None:
    step, _, arg = substep.partition(":")
    try:
        _on_message(req, message, step, _id(arg), state.data)
    except NotFoundError as exc:
        _list(req, flash=f"⚠️ {exc}")


# --- routing ---


def _on_callback(req: AdminReq, action: str, parts: list[str]) -> None:
    first = _id(parts[0]) if parts else None
    second = _id(parts[1]) if len(parts) > 1 else None
    if action == "new":
        _prompt(req, P.ASK_TITLE, "new_title", (S,))
    elif action == "new_desc_skip":
        data = _pending(req, f"{S}:new_desc")
        if data is None or not data.get("title"):
            _expired(req)
            return
        package = packages_service.create(req.db, title=data["title"], created_by=req.user_id)
        _view(req, package.id, flash=P.CREATED)
    elif first is None:  # the list, a page of it, or a malformed tap
        _list(req, page=_page(parts))
    elif action == "view":
        _view(req, first)
    elif action == "title":
        package = packages_service.get(req.db, first)
        _prompt(req, P.ASK_NEW_TITLE.format(current=package.title), f"title:{first}",
                (S, "view", first))
    elif action == "desc":
        _ask_description(req, first)
    elif action == "desc_clear":
        packages_service.update(req.db, first, description="")
        _view(req, first, flash=P.SAVED)
    elif action == "toggle":
        package = packages_service.get(req.db, first)
        active = not package.active
        packages_service.set_active(req.db, package.id, active)
        _view(req, package.id, flash=P.ACTIVATED if active else P.DEACTIVATED)
    elif action == "del_confirm":
        _confirm_delete(req, first)
    elif action == "del":
        try:
            packages_service.delete(req.db, first)
        except ValidationError as exc:
            _view(req, first, flash=f"⚠️ {exc}")
            return
        _list(req, flash=P.DELETED)
    elif action == "add":
        packages_service.get(req.db, first)
        _ask_item(req, first)
    elif action == "item":
        _item(req, first)
    elif action in ("up", "down"):
        packages_service.move_item(req.db, first, -1 if action == "up" else 1)
        _item(req, first)
    elif action == "itext":
        _ask_item_text(req, first)
    elif action == "itext_clear":
        try:
            packages_service.update_item(req.db, first, text="")
        except ValidationError as exc:  # a text item: the text is the item
            _item(req, first, flash=f"⚠️ {exc}")
            return
        _item(req, first, flash=P.SAVED)
    elif action == "ititle":
        _ask_item_title(req, first)
    elif action == "ititle_clear":
        packages_service.update_item(req.db, first, title="")
        _item(req, first, flash=P.SAVED)
    elif action == "idel_confirm":
        item = packages_service.get_item(req.db, first)
        common.render(
            req, P.ITEM_DELETE_CONFIRM.format(label=packages_service.item_label(item)),
            common.inline([[
                common.button(A.BTN_YES_DELETE, S, "idel", item.id),
                common.button(A.CANCEL, S, "item", item.id),
            ]]),
        )
    elif action == "idel":
        package_id = packages_service.delete_item(req.db, first)
        _view(req, package_id, flash=P.ITEM_DELETED)
    elif action == "copy":
        _copy(req, first)
    elif action == "send":
        _start_picker(req, first)
    elif action in ("tg", "sp", "sall", "sgo"):
        _picker_tap(req, action, first, second)
    elif action == "rcp":
        _recipients(req, first, page=_page(parts))
    elif action == "rvc":
        _confirm_revoke(req, first, from_student=parts[1:2] == ["s"])
    elif action == "rv":
        _revoke(req, first, from_student=parts[1:2] == ["s"])
    elif action == "for":
        _pick_package_for(req, first)
    elif action == "give" and second is not None:
        _give(req, first, second)
    else:
        _list(req)


def _on_message(req: AdminReq, message: dict, step: str, ident: int | None, data: dict) -> None:
    text = (message.get("text") or "").strip()
    if step == "new_title":
        try:
            title = packages_service.check_title(text)
        except ValidationError as exc:
            _prompt(req, f"⚠️ {exc}\n{P.ASK_TITLE}", "new_title", (S,))
            return
        _ask_new_description(req, title)
    elif step == "new_desc":
        _create(req, data.get("title"), message, text)
    elif step == "send":
        data["q"] = text or None  # typing a name narrows the picker
        data["page"] = 1
        _picker(req, data)
    elif ident is None:
        common.clear(req)
        _list(req)
    elif step == "title":
        try:
            packages_service.update(req.db, ident, title=text)
        except ValidationError as exc:
            package = packages_service.get(req.db, ident)
            _prompt(req, f"⚠️ {exc}\n" + P.ASK_NEW_TITLE.format(current=package.title),
                    f"title:{ident}", (S, "view", ident))
            return
        _view(req, ident, flash=P.SAVED)
    elif step == "desc":
        if not text:
            _ask_description(req, ident)
            return
        try:
            packages_service.update(req.db, ident, description=text)
        except ValidationError as exc:
            _ask_description(req, ident, warning=f"⚠️ {exc}")
            return
        _view(req, ident, flash=P.SAVED)
    elif step == "add":
        if text.startswith("/"):  # /start and the like: adding is over, not an item
            _view(req, ident)
            return
        _add(req, ident, message)
    elif step == "itext":
        new_text = text or (message.get("caption") or "").strip()
        if not new_text:
            _ask_item_text(req, ident)
            return
        packages_service.update_item(req.db, ident, text=new_text)
        _item(req, ident, flash=P.SAVED)
    elif step == "ititle":
        if not text:
            _ask_item_title(req, ident)
            return
        try:
            packages_service.update_item(req.db, ident, title=text)
        except ValidationError as exc:
            _ask_item_title(req, ident, warning=f"⚠️ {exc}")
            return
        _item(req, ident, flash=P.SAVED)
    elif step == "copy":
        try:
            packages_service.add_platform_copy(req.db, ident, message, req.ctx.platform)
        except ValidationError as exc:
            _ask_copy(req, packages_service.get_item(req.db, ident), warning=f"⚠️ {exc}")
            return
        _item(req, ident, flash=P.COPY_SAVED.format(platform=_label(req.ctx.platform)))
    else:
        common.clear(req)
        _list(req)


# --- small helpers ---


def _id(value: str) -> int | None:
    return int(value) if value.isascii() and value.isdigit() else None


def _page(parts: list[str]) -> int:
    """The page of a pager button (`…:page:<n>`), else 1."""
    if len(parts) >= 2 and parts[-2] == "page":
        return _id(parts[-1]) or 1
    return 1


def _prompt(req: AdminReq, text: str, substep: str, cancel_parts: tuple,
            rows: list | None = None, data: dict | None = None) -> None:
    common.prompt(req, text, f"{S}:{substep}", data or {},
                  keyboard=common.cancel_keyboard(cancel_parts, rows=rows))


def _pending(req: AdminReq, step: str) -> dict | None:
    """The in-progress data, if the chat is still at `step`."""
    state = req.store.get(req.ctx.platform, req.chat_id)
    return state.data if state is not None and state.step == step else None


def _expired(req: AdminReq) -> None:
    common.render(req, P.STEP_EXPIRED, common.inline([
        [common.button(P.BTN_PACKAGES, S)],
        [common.home_button()],
    ]))


def _with_flash(flash: str | None, body: str) -> str:
    return f"{flash}\n\n{body}" if flash else body


def _excerpt(text: str, limit: int) -> str:
    return text if len(text) <= limit else f"{text[:limit].rstrip()}…"


def _label(platform: Platform) -> str:
    return P.PLATFORM_LABELS.get(platform.value, platform.value)


def _other(platform: Platform) -> Platform:
    return Platform.BALE if platform == Platform.TELEGRAM else Platform.TELEGRAM


def _availability(item) -> str:
    """«تلگرام ✅ · بله ⚪» — which messengers' students get the file itself."""
    tg, bale = ("✅" if packages_service.file_id_for(item, p) else "⚪" for p in _BOT_PLATFORMS)
    return P.AVAILABILITY.format(
        tg=_label(Platform.TELEGRAM), tg_mark=tg, bale=_label(Platform.BALE), bale_mark=bale
    )


def _item_button_label(position: int, item) -> str:
    return f"{position}. {packages_service.item_icon(item)} {packages_service.item_label(item)}"


# --- packages list + one package ---


def _list(req: AdminReq, page: int = 1, flash: str | None = None) -> None:
    packages = packages_service.list_packages(req.db)
    ids = [p.id for p in packages]
    counts = packages_service.item_counts(req.db, ids)
    recipients = packages_service.recipient_counts(req.db, ids)
    pages = max((len(packages) + _PER_PAGE - 1) // _PER_PAGE, 1)
    page = max(min(page, pages), 1)
    rows = [[common.button(P.BTN_NEW, S, "new")]]
    for package in packages[(page - 1) * _PER_PAGE: page * _PER_PAGE]:
        label = P.LIST_ROW.format(
            dot="🟢" if package.active else "⚪", title=package.title,
            n=counts[package.id], r=recipients[package.id],
        )
        rows.append([common.button(label, S, "view", package.id)])
    body = f"{P.LIST_TITLE}\n{P.LIST_HINT if packages else P.NO_PACKAGES}"
    common.render(req, _with_flash(flash, body),
                  common.pager(rows, page, pages, (S, "list"), ("plans",)))


def _view(req: AdminReq, package_id: int, flash: str | None = None) -> None:
    package = packages_service.get(req.db, package_id)
    items = packages_service.items(req.db, package.id)
    recipients = packages_service.recipient_counts(req.db, [package.id])[package.id]
    status = P.STATUS_ACTIVE if package.active else P.STATUS_INACTIVE
    lines = [f"📦 {package.title}", f"{status} · {P.RECIPIENTS_COUNT.format(n=recipients)}"]
    if package.description:
        lines += ["", _excerpt(package.description, _DESCRIPTION_EXCERPT)]
    lines.append("")
    if items:
        lines.append(P.ITEMS_HEADER.format(n=len(items)))
        for position, item in enumerate(items, start=1):
            line = _item_button_label(position, item)
            if item.kind in packages_service.FILE_KINDS:
                line = f"{line} — {_availability(item)}"
            lines.append(line)
        files = [item for item in items if item.kind in packages_service.FILE_KINDS]
        for platform in _BOT_PLATFORMS:
            missing = sum(1 for f in files if not packages_service.file_id_for(f, platform))
            if missing:
                lines.append(P.MISSING_COPIES.format(n=missing, platform=_label(platform)))
        lines += ["", P.ITEMS_HINT]
    else:
        lines.append(P.NO_ITEMS)

    rows = [[common.button(P.BTN_ADD_ITEM, S, "add", package.id)]]
    rows += [
        [common.button(_item_button_label(position, item), S, "item", item.id)]
        for position, item in enumerate(items, start=1)
    ]
    rows.append([
        common.button(P.BTN_SEND, S, "send", package.id),
        common.button(P.BTN_RECIPIENTS.format(n=recipients), S, "rcp", package.id),
    ])
    rows.append([
        common.button(P.BTN_EDIT_TITLE, S, "title", package.id),
        common.button(P.BTN_EDIT_DESCRIPTION, S, "desc", package.id),
    ])
    rows.append([
        common.button(P.BTN_DEACTIVATE if package.active else P.BTN_ACTIVATE,
                      S, "toggle", package.id),
        common.button(P.BTN_DELETE, S, "del_confirm", package.id),
    ])
    common.render(req, _with_flash(flash, "\n".join(lines)), common.with_back(rows, (S,)))


def _ask_new_description(req: AdminReq, title: str, warning: str | None = None) -> None:
    text = f"{warning}\n{P.ASK_DESCRIPTION}" if warning else P.ASK_DESCRIPTION
    _prompt(req, text, "new_desc", (S,), rows=[[common.button(A.SKIP, S, "new_desc_skip")]],
            data={"title": title})


def _create(req: AdminReq, title: str | None, message: dict, text: str) -> None:
    """The description step's answer: a description, or straight away the first file."""
    if not title:
        _expired(req)
        return
    if packages_service.file_in_message(message) is not None:
        # No description — the package starts with this file as its first item.
        package = packages_service.create(req.db, title=title, created_by=req.user_id)
        _add(req, package.id, message)
        return
    if not text:  # a sticker or the like: ask again rather than guess
        _ask_new_description(req, title)
        return
    try:
        package = packages_service.create(
            req.db, title=title, description=text, created_by=req.user_id
        )
    except ValidationError as exc:
        _ask_new_description(req, title, warning=f"⚠️ {exc}")
        return
    _view(req, package.id, flash=P.CREATED)


def _ask_description(req: AdminReq, package_id: int, warning: str | None = None) -> None:
    package = packages_service.get(req.db, package_id)
    rows = None
    if package.description:
        text = P.ASK_NEW_DESCRIPTION.format(current=package.description)
        rows = [[common.button(P.BTN_CLEAR_DESCRIPTION, S, "desc_clear", package.id)]]
    else:
        text = P.ASK_SET_DESCRIPTION
    _prompt(req, f"{warning}\n{text}" if warning else text, f"desc:{package.id}",
            (S, "view", package.id), rows=rows)


def _confirm_delete(req: AdminReq, package_id: int) -> None:
    package = packages_service.get(req.db, package_id)
    if packages_service.ever_assigned(req.db, package.id):
        # Refused up front: no point asking about a delete that cannot happen.
        _view(req, package.id, flash=f"⚠️ {P.DELETE_REFUSED}")
        return
    common.render(req, P.DELETE_CONFIRM.format(title=package.title), common.inline([[
        common.button(A.BTN_YES_DELETE, S, "del", package.id),
        common.button(A.CANCEL, S, "view", package.id),
    ]]))


# --- items ---


def _ask_item(req: AdminReq, package_id: int, text: str = P.ASK_ITEM,
              warning: str | None = None) -> None:
    """Stay in «add» until «✅ تمام»: an album of videos arrives as one message
    each, and every one of them becomes an item."""
    common.prompt(
        req, f"{warning}\n{text}" if warning else text, f"{S}:add:{package_id}", {},
        keyboard=common.inline([[common.button(P.BTN_DONE_ADDING, S, "view", package_id)]]),
    )


def _add(req: AdminReq, package_id: int, message: dict) -> None:
    try:
        item = packages_service.add_item_from_message(
            req.db, package_id, message, req.ctx.platform
        )
    except ValidationError as exc:
        _ask_item(req, package_id, warning=f"⚠️ {exc}")
        return
    count = packages_service.item_counts(req.db, [package_id])[package_id]
    _ask_item(req, package_id,
              text=P.ITEM_ADDED.format(label=packages_service.item_label(item), n=count))


def _item(req: AdminReq, item_id: int, flash: str | None = None) -> None:
    item = packages_service.get_item(req.db, item_id)
    siblings = packages_service.items(req.db, item.package_id)
    position = next(i for i, sibling in enumerate(siblings, start=1) if sibling.id == item.id)
    kind = f"{packages_service.item_icon(item)} {P.KIND_NAMES.get(item.kind, item.kind)}"
    if item.original_filename:
        kind = f"{kind} · {item.original_filename}"
    is_file = item.kind in packages_service.FILE_KINDS
    lines = [
        P.ITEM_TITLE.format(package=item.package.title, pos=position, total=len(siblings)),
        kind,
        f"{P.LABEL_ITEM_TITLE}: {item.title or P.EMPTY_VALUE}",
        f"{P.LABEL_ITEM_TEXT}: "
        f"{_excerpt(item.text, _TEXT_EXCERPT) if item.text else P.EMPTY_VALUE}",
        "",
        f"📲 {_availability(item)}" if is_file else P.TEXT_EVERYWHERE,
    ]
    rows = [
        [common.button(A.BTN_MOVE_UP, S, "up", item.id),
         common.button(A.BTN_MOVE_DOWN, S, "down", item.id)],
        [common.button(P.BTN_EDIT_TEXT, S, "itext", item.id),
         common.button(P.BTN_EDIT_ITEM_TITLE, S, "ititle", item.id)],
    ]
    copy = _copy_button(req, item)
    if copy is not None:
        rows.append([copy])
    rows.append([common.button(P.BTN_DELETE_ITEM, S, "idel_confirm", item.id)])
    common.render(req, _with_flash(flash, "\n".join(lines)),
                  common.with_back(rows, (S, "view", item.package_id)))


def _ask_item_text(req: AdminReq, item_id: int) -> None:
    item = packages_service.get_item(req.db, item_id)
    current = _excerpt(item.text, 1000) if item.text else P.EMPTY_VALUE
    rows = None
    if item.text and item.kind != "text":  # a caption may go; a text item's text may not
        rows = [[common.button(P.BTN_CLEAR_TEXT, S, "itext_clear", item.id)]]
    _prompt(req, P.ASK_ITEM_TEXT.format(current=current), f"itext:{item.id}",
            (S, "item", item.id), rows=rows)


def _ask_item_title(req: AdminReq, item_id: int, warning: str | None = None) -> None:
    item = packages_service.get_item(req.db, item_id)
    text = P.ASK_ITEM_TITLE.format(current=item.title or P.EMPTY_VALUE)
    rows = [[common.button(P.BTN_CLEAR_TITLE, S, "ititle_clear", item.id)]] if item.title else None
    _prompt(req, f"{warning}\n{text}" if warning else text, f"ititle:{item.id}",
            (S, "item", item.id), rows=rows)


# --- the other messenger's copy of a file ---


def _copy_button(req: AdminReq, item) -> dict | None:
    """«📲 افزودن نسخهٔ <here>» when this bot lacks the file (send it now), else
    «📲 نسخهٔ <other>» while the other bot lacks it (how to add it there)."""
    if item.kind not in packages_service.FILE_KINDS:
        return None
    here = req.ctx.platform
    if not packages_service.file_id_for(item, here):
        return common.button(P.BTN_ADD_COPY_HERE.format(platform=_label(here)), S, "copy", item.id)
    if not packages_service.file_id_for(item, _other(here)):
        return common.button(P.BTN_COPY.format(platform=_label(_other(here))), S, "copy", item.id)
    return None


def _copy(req: AdminReq, item_id: int) -> None:
    item = packages_service.get_item(req.db, item_id)
    here, other = req.ctx.platform, _other(req.ctx.platform)
    if item.kind not in packages_service.FILE_KINDS:
        _item(req, item.id)
    elif not packages_service.file_id_for(item, here):
        _ask_copy(req, item)  # the coach is on the platform missing it: capture it now
    elif not packages_service.file_id_for(item, other):
        # A file_id from this bot is useless on the other one: it has to come from there.
        common.render(req, P.COPY_HOWTO.format(have=_label(here), missing=_label(other)),
                      common.with_back([], (S, "item", item.id)))
    else:
        _item(req, item.id)


def _ask_copy(req: AdminReq, item, warning: str | None = None) -> None:
    text = P.ASK_COPY.format(kind=P.KIND_NAMES[item.kind], platform=_label(req.ctx.platform))
    _prompt(req, f"{warning}\n{text}" if warning else text, f"copy:{item.id}",
            (S, "item", item.id))


# --- sending to students (multi-select) ---


def _start_picker(req: AdminReq, package_id: int, flash: str | None = None) -> None:
    package = packages_service.get(req.db, package_id)
    if not package.active:
        _view(req, package.id, flash=f"⚠️ {P.SEND_INACTIVE}")
    elif not packages_service.item_counts(req.db, [package.id])[package.id]:
        _view(req, package.id, flash=f"⚠️ {P.SEND_EMPTY}")
    else:
        _picker(req, {"pid": package.id, "sel": [], "page": 1, "q": None}, flash=flash)


def _picker_tap(req: AdminReq, action: str, package_id: int, arg: int | None) -> None:
    state = req.store.get(req.ctx.platform, req.chat_id)
    if state is None or state.step != _SEND_STEP or state.data.get("pid") != package_id:
        # A restart, or a button from an older picker: start over, and say so.
        _start_picker(req, package_id, flash=P.PICK_EXPIRED)
        return
    data = state.data
    if action == "sgo":
        if data["sel"]:
            _send(req, data)
            return
    elif action == "tg" and arg is not None:
        if arg not in packages_service.active_person_ids(req.db, package_id):
            data["sel"] = sorted(set(data["sel"]) ^ {arg})
    elif action == "sp" and arg is not None:
        data["page"] = arg
    elif action == "sall":
        data["q"], data["page"] = None, 1
    _picker(req, data)


def _picker(req: AdminReq, data: dict, flash: str | None = None) -> None:
    """Every student, online ones first: 🟢/⚪ toggles, ✅ for those who have it."""
    package = packages_service.get(req.db, data["pid"])
    query = data.get("q")
    has = packages_service.active_person_ids(req.db, package.id)
    people = sorted(
        req.db.scalars(persons_service.search_stmt(Role.CLIENT, query, None)),
        key=lambda p: (p.id in has, p.student_type != StudentType.ONLINE, p.name),
    )
    selected = set(data["sel"])
    pages = max((len(people) + _PICK_PER_PAGE - 1) // _PICK_PER_PAGE, 1)
    page = data["page"] = max(min(data.get("page") or 1, pages), 1)

    rows = []
    for person in people[(page - 1) * _PICK_PER_PAGE: page * _PICK_PER_PAGE]:
        icon = programs_admin._TYPE_ICONS.get(person.student_type, "")
        if person.id in has:
            label = P.PICK_HAS.format(icon=icon, name=person.name)
        else:
            dot = "🟢" if person.id in selected else "⚪"
            label = P.PICK_ROW.format(dot=dot, icon=icon, name=person.name)
        rows.append([common.button(label, S, "tg", package.id, person.id)])
    nav = []
    if page > 1:
        nav.append(common.button(A.PREV, S, "sp", package.id, page - 1))
    if page < pages:
        nav.append(common.button(A.NEXT, S, "sp", package.id, page + 1))
    if nav:
        rows.append(nav)
    if selected:
        rows.append([common.button(P.BTN_SEND_TO.format(n=len(selected)), S, "sgo", package.id)])
    if query:
        rows.append([common.button(P.BTN_SHOW_ALL, S, "sall", package.id)])

    lines = [P.ASK_PICK.format(title=package.title)]
    if query:
        lines.append(P.PICK_FILTER.format(query=query))
    if not people:
        lines.append(P.PICK_NONE)
    lines.append(P.PICK_SELECTED.format(n=len(selected)))
    common.prompt_show(req, _with_flash(flash, "\n".join(lines)), _SEND_STEP, data,
                       common.with_back(rows, (S, "view", package.id)))


def _send(req: AdminReq, data: dict) -> None:
    package_id = data["pid"]
    try:
        newly = packages_service.assign(req.db, package_id, data["sel"], created_by=req.user_id)
    except ValidationError as exc:  # deactivated or emptied since the picker opened
        _view(req, package_id, flash=f"⚠️ {exc}")
        return
    _view(req, package_id, flash=P.SENT.format(n=len(newly)) if newly else P.SENT_NOBODY_NEW)


# --- recipients ---


def _recipients(req: AdminReq, package_id: int, page: int = 1, flash: str | None = None) -> None:
    package = packages_service.get(req.db, package_id)
    everyone = packages_service.recipients(req.db, package.id)
    pages = max((len(everyone) + _PER_PAGE - 1) // _PER_PAGE, 1)
    page = max(min(page, pages), 1)
    rows = [
        [common.button(P.RECIPIENT_ROW.format(name=a.person.name), "plans", "client", a.person_id),
         common.button(P.BTN_REVOKE, S, "rvc", a.id)]
        for a in everyone[(page - 1) * _PER_PAGE: page * _PER_PAGE]
    ]
    body = (f"{P.RECIPIENTS_TITLE.format(title=package.title, n=len(everyone))}\n"
            f"{P.RECIPIENTS_HINT if everyone else P.NO_RECIPIENTS}")
    common.render(req, _with_flash(flash, body),
                  common.pager(rows, page, pages, (S, "rcp", package.id), (S, "view", package.id)))


def _confirm_revoke(req: AdminReq, assignment_id: int, from_student: bool) -> None:
    """Asks first. From a student's programs screen (`…:s`) it returns there."""
    assignment = packages_service.get_assignment(req.db, assignment_id)
    origin = ("s",) if from_student else ()
    cancel = (("plans", "client", assignment.person_id) if from_student
              else (S, "rcp", assignment.package_id))
    common.render(
        req,
        P.REVOKE_CONFIRM.format(name=assignment.person.name, title=assignment.package.title),
        common.inline([[
            common.button(P.BTN_YES_REVOKE, S, "rv", assignment.id, *origin),
            common.button(A.CANCEL, *cancel),
        ]]),
    )


def _revoke(req: AdminReq, assignment_id: int, from_student: bool) -> None:
    assignment = packages_service.unassign(req.db, assignment_id)
    flash = P.REVOKED.format(name=assignment.person.name, title=assignment.package.title)
    if from_student:
        programs_admin._client(req, assignment.person_id, flash=flash)
    else:
        _recipients(req, assignment.package_id, flash=flash)


# --- one student (from their programs screen) ---


def _pick_package_for(req: AdminReq, person_id: int, flash: str | None = None) -> None:
    person = persons_service.get(req.db, person_id)
    packages = packages_service.list_packages(req.db, only_active=True)
    counts = packages_service.item_counts(req.db, [p.id for p in packages])
    has = {a.package_id for a in packages_service.assignments_for_person(req.db, person.id)}
    rows = []
    for package in packages:
        if package.id in has:
            label = P.PICK_PACKAGE_HAS.format(title=package.title)
        else:
            label = P.PICK_PACKAGE_ROW.format(title=package.title, n=counts[package.id])
        rows.append([common.button(label, S, "give", person.id, package.id)])
    if packages:
        body = P.ASK_PICK_PACKAGE.format(name=person.name)
    else:
        body = P.NO_ACTIVE_PACKAGES
        rows.append([common.button(P.BTN_PACKAGES, S)])
    common.render(req, _with_flash(flash, body),
                  common.with_back(rows, ("plans", "client", person.id)))


def _give(req: AdminReq, person_id: int, package_id: int) -> None:
    person = persons_service.get(req.db, person_id)
    try:
        newly = packages_service.assign(req.db, package_id, [person.id], created_by=req.user_id)
    except ValidationError as exc:  # an empty package: nothing to open yet
        _pick_package_for(req, person.id, flash=f"⚠️ {exc}")
        return
    package = packages_service.get(req.db, package_id)
    if newly:
        flash = P.GIVEN.format(title=package.title, name=person.name)
    else:
        flash = P.ALREADY_HAS.format(name=person.name)
    programs_admin._client(req, person.id, flash=flash)
