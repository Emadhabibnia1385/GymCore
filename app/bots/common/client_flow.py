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
from app.copy import texts
from app.core.config import get_settings
from app.models import Person
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
from app.services import plans as plans_service
from app.services import settings as settings_service

logger = logging.getLogger(__name__)


def display_name(from_user: dict) -> str:
    parts = [from_user.get("first_name"), from_user.get("last_name")]
    name = " ".join(p for p in parts if p).strip()
    return name or (from_user.get("username") or "").strip()


def provision(ctx: BotContext, db: Session, from_user: dict) -> Person:
    """Resolve (auto-creating on first contact) the Person for this account."""
    user_id = str(from_user.get("id"))
    person = identities_service.get_or_create_person(
        db,
        ctx.platform,
        user_id,
        display_name(from_user),
        username=from_user.get("username"),
    )
    auth.sync_owner_role(db, ctx.platform, user_id, person)
    return person


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
    from app.bots.common import formatting

    course = courses_service.get(db, course_id)
    if course.client_id != person.id:  # authorization: clients see only their own
        ctx.show(chat_id, texts.NOT_FOUND, keyboards.back_to_menu(), message_id)
        return
    body = formatting.format_course_detail(db, course)
    ctx.show(chat_id, body, keyboards.course_detail_nav(), message_id)


def my_programs(
    ctx: BotContext, db: Session, chat_id: object, person: Person, message_id: int | None
) -> None:
    from app.bots.common import formatting

    assignments = plans_service.list_assignments(db, person_id=person.id, only_active=True)
    if not assignments:
        # Empty state: the same blue «سفارش برنامه» button to order a program.
        url = settings_service.get_value(db, KEY_SIGNUP_URL) or get_settings().signup_url
        ctx.show(chat_id, texts.NO_PROGRAMS, keyboards.order_prompt(url), message_id)
        return
    items = [(a.id, formatting.program_label(a)) for a in assignments]
    ctx.show(chat_id, texts.TITLE_MY_PROGRAMS, keyboards.program_list(items), message_id)


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


def _deliver_program(ctx: BotContext, assignment, chat_id: object, caption: str) -> None:
    """Send the program's file (platform file_id or uploaded file), else the caption."""
    # 1. A platform file_id captured on THIS platform is the cheapest delivery
    #    (try as a document, then as a photo for image programs).
    if assignment.platform_file_id and assignment.file_platform == ctx.platform:
        try:
            ctx.client.send_document_id(chat_id, assignment.platform_file_id, caption)
            return
        except BotApiError:
            try:
                ctx.client.send_photo_id(chat_id, assignment.platform_file_id, caption)
                return
            except BotApiError:
                logger.warning("file_id delivery failed; falling back")
    # 2. An uploaded file under the (access-controlled) upload dir.
    path = plans_service.attachment_path(assignment)
    if path is not None:
        try:
            ctx.client.send_document_path(
                chat_id, path, assignment.original_filename or path.name, caption
            )
            return
        except BotApiError:
            logger.warning("file upload delivery failed; sending caption only")
    # 3. Text-only program (no attachment).
    ctx.send(chat_id, caption)


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
    elif action == cb.PROGRAMS:
        assignment_id = cb.parse_int(rest)
        if assignment_id is not None:
            program_detail(ctx, db, chat_id, person, assignment_id, message_id)
        else:
            my_programs(ctx, db, chat_id, person, message_id)
    elif action == cb.NOOP:
        return
    else:
        show_menu(ctx, db, chat_id, user_id, person, message_id)


def contact_us(
    ctx: BotContext, db: Session, chat_id: object, person: Person, message_id: int | None
) -> None:
    intro = settings_service.get_value(db, KEY_CONTACT_INTRO)
    _render_contact_links(ctx, db, chat_id, intro, message_id)
