"""Client-facing bot conversation — pure inline navigation, no forms.

One implementation serves Telegram and Bale (the BotContext adapts platform
differences). Every screen is reachable by inline buttons; there is no
registration form and no phone collection anywhere in this flow.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.bots.common import callbacks as cb
from app.bots.common import keyboards
from app.bots.common.client import BotApiError
from app.bots.common.context import BotContext
from app.copy import packages_texts as P
from app.copy import texts
from app.core.admin_auth import is_owner
from app.core.config import get_settings
from app.core.phone import is_valid_phone, normalize_phone
from app.models import Person, Platform
from app.models.setting import (
    KEY_CONTACT_INTRO,
    KEY_MAIN_INTRO,
    KEY_PLAN_ORDER_TEXT,
    KEY_REGISTER_CONTACT_TEXT,
    KEY_SIGNUP_URL,
)
from app.services import auth
from app.services import contact_links as contact_links_service
from app.services import courses as courses_service
from app.services import identities as identities_service
from app.services import packages as packages_service
from app.services import plans as plans_service
from app.services import schedule as schedule_service
from app.services import settings as settings_service

logger = logging.getLogger(__name__)


def display_name(from_user: dict) -> str:
    parts = [from_user.get("first_name"), from_user.get("last_name")]
    name = " ".join(p for p in parts if p).strip()
    return name or (from_user.get("username") or "").strip()


def _provision_owner(ctx: BotContext, db: Session, from_user: dict) -> Person:
    user_id = str(from_user.get("id"))
    person = identities_service.get_or_create_person(
        db, ctx.platform, user_id, display_name(from_user), username=from_user.get("username")
    )
    auth.sync_owner_role(db, ctx.platform, user_id, person)
    return person


def provision_for_callback(ctx: BotContext, db: Session, from_user: dict) -> Person | None:
    """Return the registered Person for a callback, or None if not registered."""
    user_id = str(from_user.get("id"))
    if is_owner(ctx.platform, user_id):
        return _provision_owner(ctx, db, from_user)
    identity = identities_service.find_identity(db, ctx.platform, user_id)
    if identity is not None and identity.person.phone:
        return identity.person
    return None


def resolve_registered(
    ctx: BotContext, db: Session, chat_id: object, from_user: dict, message: dict
) -> Person | None:
    """Resolve the Person for a message, collecting a phone on first contact.

    Everyone (except owners) shares their phone once, so their Telegram and Bale
    accounts map to the SAME Person and see the same courses/programs. Returns
    None when we've just prompted for (or rejected) a phone.
    """
    user_id = str(from_user.get("id"))
    if is_owner(ctx.platform, user_id):
        return _provision_owner(ctx, db, from_user)

    identity = identities_service.find_identity(db, ctx.platform, user_id)
    if identity is not None and identity.person.phone:
        return identity.person

    # A shared contact or a typed phone number completes registration.
    raw = (message.get("contact") or {}).get("phone_number")
    if not raw:
        text = (message.get("text") or "").strip()
        if text and is_valid_phone(normalize_phone(text)):
            raw = text
    if raw:
        if not is_valid_phone(normalize_phone(raw)):
            ctx.send(chat_id, texts.INVALID_PHONE, keyboards.share_phone())
            return None
        person = identities_service.link_by_phone(
            db, ctx.platform, user_id, raw, display_name(from_user),
            username=from_user.get("username"),
        )
        ctx.send(chat_id, texts.REGISTERED, keyboards.remove_keyboard())
        return person

    ctx.send(chat_id, texts.ASK_PHONE, keyboards.share_phone())
    return None


# --- screens ---


def show_menu(
    ctx: BotContext,
    db: Session,
    chat_id: object,
    user_id: str,
    person: Person,
    message_id: int | None = None,
    greet: bool = False,
) -> None:
    is_admin = auth.is_admin(db, ctx.platform, user_id)
    # The start screen is identical everywhere (so «بازگشت به منوی اصلی» === /start).
    intro = settings_service.get_value(db, KEY_MAIN_INTRO)
    body = f"{intro}\n\n{texts.MENU_PROMPT}"
    signup_url = settings_service.get_value(db, KEY_SIGNUP_URL) or get_settings().signup_url
    keyboard = keyboards.main_menu(is_admin, signup_url)
    poster_id = settings_service.get_value(db, settings_service.start_poster_key(ctx.platform))
    if poster_id:
        ctx.send_photo(chat_id, poster_id, caption=body, keyboard=keyboard,
                       replace_message_id=message_id)
    else:
        ctx.show(chat_id, body, keyboard, message_id)


def _render_contact_links(
    ctx: BotContext, db: Session, chat_id: object, intro: str, message_id: int | None
) -> None:
    """Show contact links: button-safe URLs as buttons, mailto:/tel: as text.

    Telegram/Bale reject mailto:/tel: in inline buttons (BUTTON_URL_INVALID),
    which previously failed the whole message — so those are rendered as
    copyable text lines instead.
    """
    links = contact_links_service.list_active(db, ctx.platform)
    support_copy = ctx.supports_copy_text

    # With copy buttons (Telegram) every link is a button; otherwise mailto:/tel:
    # links are shown as text (they can't be inline buttons).
    text_links = [] if support_copy else [ln for ln in links if not keyboards.is_button_url(ln.url)]
    body = intro
    if text_links:
        lines = []
        for link in text_links:
            value = link.url.split(":", 1)[1] if ":" in link.url else link.url
            icon = f"{link.icon} " if link.icon else ""
            lines.append(f"{icon}{link.label}: {value}")
        body = f"{intro}\n\n" + "\n".join(lines)
    elif not links:
        body = f"{intro}\n\n{texts.NO_CONTACT_LINKS}"

    ctx.show(chat_id, body, keyboards.contact_links(links, support_copy), message_id)


def register_contact(
    ctx: BotContext, db: Session, chat_id: object, person: Person, message_id: int | None
) -> None:
    """«ثبت‌نام در کلاس‌ها» → contact methods (NO form, NO request, NO phone)."""
    intro = settings_service.get_value(db, KEY_REGISTER_CONTACT_TEXT)
    _render_contact_links(ctx, db, chat_id, intro, message_id)


def order_plan(
    ctx: BotContext, db: Session, chat_id: object, person: Person, message_id: int | None
) -> None:
    """«سفارش برنامه» fallback screen (only when the menu URL button isn't used)."""
    url = settings_service.get_value(db, KEY_SIGNUP_URL) or get_settings().signup_url
    body = settings_service.get_value(db, KEY_PLAN_ORDER_TEXT)
    ctx.show(chat_id, body, keyboards.plan_signup(url), message_id)


def my_courses(
    ctx: BotContext, db: Session, chat_id: object, person: Person, message_id: int | None
) -> None:
    courses = courses_service.list_courses(db, client_id=person.id)
    if not courses:
        # Empty state: invite the client to contact the coach to register.
        _render_contact_links(ctx, db, chat_id, texts.NO_COURSES, message_id)
        return
    items = [
        (course.id, course.class_type.title, courses_service.remaining_sessions(db, course))
        for course in courses
    ]
    ctx.show(chat_id, texts.TITLE_MY_COURSES, keyboards.course_list(items), message_id)


def course_detail(
    ctx: BotContext,
    db: Session,
    chat_id: object,
    person: Person,
    course_id: int,
    message_id: int | None,
) -> None:
    from app.bots.common import formatting, grid

    course = courses_service.get(db, course_id)
    if course.client_id != person.id:  # authorization: clients see only their own
        ctx.show(chat_id, texts.NOT_FOUND, keyboards.back_to_menu(), message_id)
        return
    # Course info (no money, no text history) followed by the colour-coded grid
    # itself, then back to «کلاس‌های من» and «منوی اصلی».
    body = formatting.format_course_detail(db, course, show_history=False, show_financial=False)
    slots = schedule_service.build(db, course)
    if len(slots) > grid.MAX_ROWS_PER_SCREEN:
        # Past ~100 buttons the platforms refuse the whole message: a long course
        # opens its paged grid from a button instead.
        ctx.show(chat_id, body, keyboards.course_detail_nav(course.id), message_id)
        return
    rows = grid.client_rows(slots)
    rows.append([keyboards.button(texts.BTN_BACK, cb.COURSES, keyboards.STYLE_DANGER)])
    rows.append([keyboards.home_button()])
    ctx.show(chat_id, body, {"inline_keyboard": rows}, message_id)


def course_schedule(
    ctx: BotContext,
    db: Session,
    chat_id: object,
    person: Person,
    course_id: int,
    page: int,
    message_id: int | None,
) -> None:
    """«جدول جلسات» — the same grid the coach uses, read-only for the client."""
    from app.bots.common import grid

    course = courses_service.get(db, course_id)
    if course.client_id != person.id:  # authorization: clients see only their own
        ctx.show(chat_id, texts.NOT_FOUND, keyboards.back_to_menu(), message_id)
        return
    slots = schedule_service.build(db, course)
    if not slots:
        ctx.show(chat_id, texts.GRID_EMPTY, keyboards.course_detail_nav(course.id), message_id)
        return
    visible, page, pages = grid.page_slice(slots, page)
    body = (
        f"{grid.header(db, course, page, pages, for_admin=False)}"
        f"\n\n{texts.GRID_HINT_CLIENT}"
    )
    keyboard = keyboards.session_grid(grid.client_rows(visible), course.id, page, pages)
    ctx.show(chat_id, body, keyboard, message_id)


def my_programs(
    ctx: BotContext, db: Session, chat_id: object, person: Person, message_id: int | None
) -> None:
    from app.bots.common import formatting

    packages = packages_service.list_for_person(db, person.id)
    assignments = plans_service.list_assignments(db, person_id=person.id, only_active=True)
    if not packages and not assignments:
        # Empty state: the same blue «سفارش برنامه» button to order a program.
        url = settings_service.get_value(db, KEY_SIGNUP_URL) or get_settings().signup_url
        ctx.show(chat_id, texts.NO_PROGRAMS, keyboards.order_prompt(url), message_id)
        return
    # Packages first — they are the coach's courses — then single programs.
    counts = packages_service.item_counts(db, [p.id for p in packages])
    bundles = [
        (p.id, P.STUDENT_PACKAGE_ROW.format(title=p.title, n=counts[p.id])) for p in packages
    ]
    items = [(a.id, formatting.program_label(a)) for a in assignments]
    ctx.show(chat_id, texts.TITLE_MY_PROGRAMS, keyboards.program_list(items, bundles), message_id)


def package_detail(
    ctx: BotContext,
    db: Session,
    chat_id: object,
    person: Person,
    package_id: int,
    message_id: int | None,
) -> None:
    """A package the student was given: its description, then one button per item."""
    package = packages_service.open_for(db, package_id, person.id)
    if package is None:  # authorization: only packages actively theirs, and active
        ctx.show(chat_id, texts.NOT_FOUND, keyboards.back_to_menu(), message_id)
        return
    keyboard, has_items = _package_keyboard(db, package)
    lines = [f"📦 {package.title}"]
    if package.description:
        lines += ["", package.description]
    lines += ["", P.STUDENT_PACKAGE_HINT if has_items else P.STUDENT_PACKAGE_EMPTY]
    ctx.show(chat_id, "\n".join(lines), keyboard, message_id)


def package_item(
    ctx: BotContext,
    db: Session,
    chat_id: object,
    person: Person,
    package_id: int,
    item_id: int | None,
    message_id: int | None,
) -> None:
    """Deliver one item of the student's package, then its items again below it."""
    package = packages_service.open_for(db, package_id, person.id)
    item = packages_service.find_item(db, item_id) if item_id is not None else None
    if package is None or item is None or item.package_id != package.id:
        ctx.show(chat_id, texts.NOT_FOUND, keyboards.back_to_menu(), message_id)
        return
    _deliver_item(ctx, item, chat_id)
    # A fresh screen under what was just sent: the next item is one tap away.
    keyboard, _ = _package_keyboard(db, package)
    ctx.send(chat_id, P.ITEM_SENT.format(label=packages_service.item_label(item)), keyboard)


def _package_keyboard(db: Session, package) -> tuple[dict, bool]:
    """The package's items as buttons, and whether it has any."""
    items = packages_service.items(db, package.id)
    labels = [
        (item.id, f"{packages_service.item_icon(item)} {packages_service.item_label(item)}")
        for item in items
    ]
    return keyboards.package_items(package.id, labels), bool(items)


def program_detail(
    ctx: BotContext,
    db: Session,
    chat_id: object,
    person: Person,
    assignment_id: int,
    message_id: int | None,
) -> None:
    from app.bots.common import formatting

    assignment = plans_service.get_assignment(db, assignment_id)
    if assignment.person_id != person.id:  # authorization
        ctx.show(chat_id, texts.NOT_FOUND, keyboards.back_to_menu(), message_id)
        return
    caption = formatting.format_program_caption(assignment)
    _deliver_program(ctx, assignment, chat_id, caption)
    ctx.send(chat_id, texts.PROGRAM_SENT, keyboards.program_detail_nav())


# Both platforms cap a file caption at 1024 characters and a message at 4096;
# past either, the send fails outright. A long coach note therefore travels as
# its own message(s) after the file instead of taking the file down with it.
_CAPTION_LIMIT = 1024
_MESSAGE_LIMIT = 4096

# file_kind → the BotClient method that re-sends a file_id of that kind.
_FILE_ID_SENDERS = {
    "document": "send_document_id",
    "photo": "send_photo_id",
    "video": "send_video_id",
}


def _chunks(text: str, limit: int = _MESSAGE_LIMIT) -> list[str]:
    """Split text into sendable pieces, at line breaks where possible."""
    pieces: list[str] = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        cut = cut if cut > 0 else limit
        pieces.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return [*pieces, text] if text else pieces


def _deliver_program(ctx: BotContext, assignment, chat_id: object, caption: str) -> None:
    """Send the program's file (platform file_id or uploaded file), else the caption."""
    from app.bots.common import formatting

    file_caption, follow_up = caption, None
    if len(caption) > _CAPTION_LIMIT:
        file_caption = formatting.format_program_caption(assignment, with_note=False)
        follow_up = caption

    def _sent_file() -> bool:
        # 1. A platform file_id captured on THIS platform is the cheapest delivery:
        #    one call by its kind, or — for programs from before kinds were
        #    recorded — as a document, then as a photo.
        if assignment.platform_file_id and assignment.file_platform == ctx.platform:
            kinds = (
                [assignment.file_kind] if assignment.file_kind in _FILE_ID_SENDERS
                else ["document", "photo"]
            )
            for kind in kinds:
                try:
                    getattr(ctx.client, _FILE_ID_SENDERS[kind])(
                        chat_id, assignment.platform_file_id, file_caption
                    )
                    return True
                except BotApiError:
                    continue
            logger.warning("file_id delivery failed; falling back")
        # 2. An uploaded file under the (access-controlled) upload dir.
        path = plans_service.attachment_path(assignment)
        if path is not None:
            try:
                ctx.client.send_document_path(
                    chat_id, path, assignment.original_filename or path.name, file_caption
                )
                return True
            except BotApiError:
                logger.warning("file upload delivery failed; sending caption only")
        return False

    if _sent_file():
        texts_after = _chunks(follow_up) if follow_up else []
    else:
        texts_after = _chunks(caption)  # 3. A text-only program (or no file reached).
    _send_content(ctx, chat_id, texts_after)


def _send_content(ctx: BotContext, chat_id: object, pieces: list[str]) -> None:
    """Send what the student came for as messages that stay in the chat.

    Untracked: a tracked send is the chat's one "screen", deleted by the next
    screen — the nav message sent right after would take the program with it.
    """
    for piece in pieces:
        ctx.send(chat_id, piece, track=False)


def _deliver_item(ctx: BotContext, item, chat_id: object) -> None:
    """Send one package item on THIS platform.

    A file goes out by its kind — one call — with the item's words as caption
    (or after it, past the caption limit). When this platform holds no copy of
    the file, the student gets the words and where the file is instead.
    """
    words = packages_service.item_caption(item)
    after = words
    if item.kind in _FILE_ID_SENDERS:
        file_id = packages_service.file_id_for(item, ctx.platform)
        if file_id is None:
            other = Platform.BALE if ctx.platform == Platform.TELEGRAM else Platform.TELEGRAM
            note = P.FILE_ON_OTHER.format(platform=P.PLATFORM_LABELS[other.value])
            after = "\n\n".join(part for part in (words, note) if part)
        else:
            caption, after = words, ""
            if len(words) > _CAPTION_LIMIT:
                caption, after = (item.title or "")[:_CAPTION_LIMIT], words
            try:
                getattr(ctx.client, _FILE_ID_SENDERS[item.kind])(chat_id, file_id, caption)
            except BotApiError:
                logger.warning("package item %s: file_id delivery failed", item.id)
                after = "\n\n".join(part for part in (words, P.FILE_FAILED) if part)
    _send_content(ctx, chat_id, _chunks(after) if after else [])


# --- callback routing ---


def route(
    ctx: BotContext,
    db: Session,
    chat_id: object,
    user_id: str,
    person: Person,
    message_id: int | None,
    action: str,
    rest: str | None,
) -> None:
    if action == cb.HOME:
        show_menu(ctx, db, chat_id, user_id, person, message_id)
    elif action == cb.REGISTER:
        register_contact(ctx, db, chat_id, person, message_id)
    elif action == cb.ORDER:
        order_plan(ctx, db, chat_id, person, message_id)
    elif action == cb.CONTACT:
        contact_us(ctx, db, chat_id, person, message_id)
    elif action == cb.COURSES:
        course_id = cb.parse_int(rest)
        if course_id is not None:
            course_detail(ctx, db, chat_id, person, course_id, message_id)
        else:
            my_courses(ctx, db, chat_id, person, message_id)
    elif action == cb.SCHEDULE:
        course_id, page = cb.parse_pair(rest)
        if course_id is None:
            my_courses(ctx, db, chat_id, person, message_id)
        else:
            course_schedule(ctx, db, chat_id, person, course_id, page, message_id)
    elif action == cb.PROGRAMS:
        assignment_id = cb.parse_int(rest)
        if assignment_id is not None:
            program_detail(ctx, db, chat_id, person, assignment_id, message_id)
        else:
            my_programs(ctx, db, chat_id, person, message_id)
    elif action == cb.PACKAGE:
        # 'pk:<package>' opens a package, 'pk:<package>:<item>' sends one item.
        first, _, second = (rest or "").partition(cb.SEP)
        package_id = cb.parse_int(first or None)
        if package_id is None:
            my_programs(ctx, db, chat_id, person, message_id)
        elif not second:
            package_detail(ctx, db, chat_id, person, package_id, message_id)
        else:
            package_item(
                ctx, db, chat_id, person, package_id, cb.parse_int(second), message_id
            )
    elif action == cb.NOOP:
        return
    else:
        show_menu(ctx, db, chat_id, user_id, person, message_id)


def contact_us(
    ctx: BotContext, db: Session, chat_id: object, person: Person, message_id: int | None
) -> None:
    intro = settings_service.get_value(db, KEY_CONTACT_INTRO)
    _render_contact_links(ctx, db, chat_id, intro, message_id)
