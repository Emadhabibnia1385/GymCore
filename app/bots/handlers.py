"""Platform-agnostic bot conversation logic.

One handler serves both Telegram and Bale — the `BotClient` and its
`platform` decide where replies go. Conversation state is a small
in-memory dict per bot process (each bot runs as its own service).

All business operations go through the shared service layer, so the
bots, the API and the web panel always behave identically.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.bots import keyboards, texts
from app.bots.client import BotClient
from app.core.exceptions import DomainError
from app.core.phone import is_valid_phone, normalize_phone
from app.db.session import SessionLocal
from app.models import CourseStatus, Person, PlanType
from app.models.setting import KEY_CONTACT_TEXT, KEY_WELCOME_TEXT
from app.services import app_settings as settings_service
from app.services import attendance as attendance_service
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import persons as persons_service
from app.services import plans as plans_service
from app.services import requests as requests_service

logger = logging.getLogger(__name__)

_COURSE_STATUS_LABELS = {
    CourseStatus.ACTIVE: "فعال",
    CourseStatus.FINISHED: "پایان‌یافته",
    CourseStatus.PAUSED: "متوقف",
}

_PLAN_TYPE_BY_BUTTON = {
    texts.BTN_PLAN_TRAINING: PlanType.TRAINING,
    texts.BTN_PLAN_NUTRITION: PlanType.NUTRITION,
    texts.BTN_PLAN_CUSTOM: PlanType.CUSTOM,
}


@dataclass
class ChatState:
    step: str = "MENU"
    data: dict = field(default_factory=dict)


class BotHandler:
    def __init__(self, client: BotClient):
        self.client = client
        self.platform = client.platform
        self.states: dict[str, ChatState] = {}

    # --- entrypoint ---

    def handle_update(self, update: dict) -> None:
        message = update.get("message")
        if not message:
            return
        chat_id = str(message["chat"]["id"])
        user_id = str(message["from"]["id"])
        text = (message.get("text") or "").strip()
        contact = message.get("contact")

        db = SessionLocal()
        try:
            self._handle_message(db, chat_id, user_id, text, contact)
        except DomainError as exc:
            self.client.send_message(chat_id, str(exc), keyboards.main_menu())
            self.states[chat_id] = ChatState()
        except Exception:
            logger.exception("Unhandled error for %s chat %s", self.platform, chat_id)
            self.client.send_message(chat_id, texts.ERROR, keyboards.main_menu())
            self.states[chat_id] = ChatState()
        finally:
            db.close()

    # --- routing ---

    def _handle_message(
        self, db: Session, chat_id: str, user_id: str, text: str, contact: dict | None
    ) -> None:
        person = persons_service.find_by_identity(db, self.platform, user_id)
        state = self.states.setdefault(chat_id, ChatState())

        # Unregistered users go through the registration flow.
        if person is None:
            self._registration_flow(db, chat_id, user_id, text, contact, state)
            return

        if text == "/start" or text == texts.BTN_BACK:
            self._show_menu(db, chat_id, greet=(text == "/start"))
            return

        step_handlers = {
            "PICK_CLASS": self._on_pick_class,
            "PICK_PLAN_TYPE": self._on_pick_plan_type,
            "PLAN_NOTE": self._on_plan_note,
        }
        if state.step in step_handlers:
            step_handlers[state.step](db, chat_id, person, text)
            return

        menu_handlers = {
            texts.BTN_REGISTER_CLASS: self._start_class_registration,
            texts.BTN_ORDER_PLAN: self._start_plan_order,
            texts.BTN_MY_CLASSES: self._show_my_classes,
            texts.BTN_MY_PLANS: self._show_my_plans,
            texts.BTN_CONTACT: self._show_contact,
        }
        handler = menu_handlers.get(text)
        if handler:
            handler(db, chat_id, person)
        else:
            self.client.send_message(chat_id, texts.UNKNOWN, keyboards.main_menu())

    # --- registration ---

    def _registration_flow(
        self,
        db: Session,
        chat_id: str,
        user_id: str,
        text: str,
        contact: dict | None,
        state: ChatState,
    ) -> None:
        if state.step == "ASK_NAME" and text and not text.startswith("/"):
            state.data["name"] = text
            state.step = "ASK_PHONE"
            self.client.send_message(chat_id, texts.ASK_PHONE, keyboards.share_phone())
            return

        if state.step == "ASK_PHONE":
            raw_phone = (contact or {}).get("phone_number") or text
            phone = normalize_phone(raw_phone)
            if not is_valid_phone(phone):
                self.client.send_message(
                    chat_id, texts.INVALID_PHONE, keyboards.share_phone()
                )
                return
            persons_service.register_from_bot(
                db, self.platform, user_id, state.data["name"], phone
            )
            self.states[chat_id] = ChatState()
            self.client.send_message(chat_id, texts.REGISTERED, keyboards.main_menu())
            return

        # Any first contact starts registration.
        welcome = settings_service.get_value(db, KEY_WELCOME_TEXT)
        state.step = "ASK_NAME"
        state.data = {}
        self.client.send_message(chat_id, f"{welcome}\n\n{texts.ASK_NAME}")

    # --- menu actions ---

    def _show_menu(self, db: Session, chat_id: str, greet: bool = False) -> None:
        self.states[chat_id] = ChatState()
        text = (
            f"{settings_service.get_value(db, KEY_WELCOME_TEXT)}\n\n{texts.MENU}"
            if greet
            else texts.BACK_TO_MENU
        )
        self.client.send_message(chat_id, text, keyboards.main_menu())

    def _start_class_registration(
        self, db: Session, chat_id: str, person: Person
    ) -> None:
        class_types = classes_service.list_class_types(db, only_active=True)
        if not class_types:
            self.client.send_message(
                chat_id, texts.NO_ACTIVE_CLASSES, keyboards.main_menu()
            )
            return
        state = self.states[chat_id]
        state.step = "PICK_CLASS"
        state.data["classes"] = {c.title: c.id for c in class_types}
        lines = [texts.CHOOSE_CLASS, ""]
        for c in class_types:
            lines.append(f"• {c.title}" + (f" — {c.description}" if c.description else ""))
        self.client.send_message(
            chat_id, "\n".join(lines), keyboards.class_list([c.title for c in class_types])
        )

    def _on_pick_class(
        self, db: Session, chat_id: str, person: Person, text: str
    ) -> None:
        class_id = self.states[chat_id].data.get("classes", {}).get(text)
        if class_id is None:
            self.client.send_message(chat_id, texts.UNKNOWN)
            return
        requests_service.create_class_request(db, person.id, class_id)
        self.states[chat_id] = ChatState()
        self.client.send_message(chat_id, texts.CLASS_REQUEST_SENT, keyboards.main_menu())

    def _start_plan_order(self, db: Session, chat_id: str, person: Person) -> None:
        self.states[chat_id].step = "PICK_PLAN_TYPE"
        self.client.send_message(chat_id, texts.CHOOSE_PLAN_TYPE, keyboards.plan_types())

    def _on_pick_plan_type(
        self, db: Session, chat_id: str, person: Person, text: str
    ) -> None:
        plan_type = _PLAN_TYPE_BY_BUTTON.get(text)
        if plan_type is None:
            self.client.send_message(chat_id, texts.UNKNOWN)
            return
        state = self.states[chat_id]
        state.step = "PLAN_NOTE"
        state.data["plan_type"] = plan_type
        self.client.send_message(chat_id, texts.ASK_PLAN_NOTE, keyboards.note_or_skip())

    def _on_plan_note(
        self, db: Session, chat_id: str, person: Person, text: str
    ) -> None:
        note = None if text == texts.BTN_NO_NOTE else text
        plan_type = self.states[chat_id].data["plan_type"]
        requests_service.create_plan_request(db, person.id, plan_type, note)
        self.states[chat_id] = ChatState()
        self.client.send_message(chat_id, texts.PLAN_REQUEST_SENT, keyboards.main_menu())

    def _show_my_classes(self, db: Session, chat_id: str, person: Person) -> None:
        courses = courses_service.list_courses(db, client_id=person.id)
        if not courses:
            self.client.send_message(chat_id, texts.NO_COURSES, keyboards.main_menu())
            return
        blocks: list[str] = []
        for course in courses:
            remaining = courses_service.remaining_sessions(db, course)
            lines = [
                f"🏷 {course.class_type.title} ({_COURSE_STATUS_LABELS[course.status]})",
                f"جلسات: {course.sessions_total} | باقی‌مانده: {remaining}",
            ]
            events = attendance_service.list_for_course(db, course.id)
            if events:
                lines.append("جلسات اخیر:")
                from app.core.jalali import format_jalali

                for event in events[-5:]:
                    lines.append(
                        f"  {format_jalali(event.session_date)} — "
                        f"{attendance_service.status_label(event.status)}"
                    )
            blocks.append("\n".join(lines))
        self.client.send_message(chat_id, "\n\n".join(blocks), keyboards.main_menu())

    def _show_my_plans(self, db: Session, chat_id: str, person: Person) -> None:
        plans = plans_service.list_plans(db, person_id=person.id, only_active=True)
        if not plans:
            self.client.send_message(chat_id, texts.NO_PLANS, keyboards.main_menu())
            return
        for plan in plans:
            caption = f"📄 {plan.title} ({plans_service.type_label(plan.plan_type)})"
            if plan.description:
                caption += f"\n\n{plan.description}"
            path = plans_service.attachment_path(plan)
            if path is not None:
                self.client.send_document(
                    chat_id, path, plan.original_filename or path.name, caption
                )
            else:
                self.client.send_message(chat_id, caption)
        self.client.send_message(chat_id, texts.MENU, keyboards.main_menu())

    def _show_contact(self, db: Session, chat_id: str, person: Person) -> None:
        contact_text = settings_service.get_value(db, KEY_CONTACT_TEXT)
        self.client.send_message(chat_id, contact_text, keyboards.main_menu())
