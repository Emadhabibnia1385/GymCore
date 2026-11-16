"""«Log in with the bot»: the Telegram side of the web panel's sign-in.

The panel's link opens the bot with `/start wl_<token>`. The bot shows who is asking (device,
time, address) and two buttons; only the person pressing «تأیید» lets that browser in. The
refuse button and the details are the defence against someone sending a victim their own link.
"""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.bots.common import callbacks as cb
from app.bots.common.context import BotContext
from app.core import clock
from app.core.jalali import format_jalali
from app.models import Person, Platform
from app.services import web_login

_TOKEN = re.compile(r"^[A-Za-z0-9_-]{16,64}$")

ASK = (
    "🔐 درخواست ورود به پنل وب\n\n"
    "کسی می‌خواهد با حساب تو وارد پنل جیم‌کور شود:\n"
    "🖥 دستگاه: {device}\n"
    "🕒 زمان: {when}\n"
    "🌐 آدرس: {ip}\n\n"
    "فقط اگر خودت همین الان در سایت «ورود با ربات» را زده‌ای تأیید کن."
)
CONFIRM = "✅ تأیید ورود"
REFUSE = "❌ نه، من نبودم"
DONE = "✅ تأیید شد؛ به پنل برگرد، خودش وارد می‌شود."
REFUSED = "❌ ورود رد شد. اگر این درخواست مال تو نبود، کاری لازم نیست."
EXPIRED = "این درخواست منقضی شده یا قبلاً جواب داده شده؛ در سایت دوباره «ورود با ربات» را بزن."
TELEGRAM_ONLY = "ورود به پنل وب فقط از ربات تلگرام ممکن است."


def token_from_start(text: str) -> str | None:
    """The token in `/start wl_<token>`, or None for any other message."""
    prefix = f"/start {web_login.START_PREFIX}"
    if not text.startswith(prefix):
        return None
    token = text[len(prefix):].strip()
    return token if _TOKEN.match(token) else ""


def offer(ctx: BotContext, db: Session, chat_id: object, token: str) -> None:
    """Show the approval message for a link the person just opened."""
    if ctx.platform != Platform.TELEGRAM:
        ctx.send(chat_id, TELEGRAM_ONLY)
        return
    request = web_login.pending(db, token) if token else None
    if request is None:
        ctx.send(chat_id, EXPIRED)
        return
    now = clock.local_now()
    text = ASK.format(
        device=web_login.describe_device(request.user_agent),
        when=f"{format_jalali(now.date())} {now:%H:%M}",
        ip=request.client_ip or "—",
    )
    ctx.send(chat_id, text, {"inline_keyboard": [[
        {"text": CONFIRM, "callback_data": f"{cb.WEB_LOGIN}{cb.SEP}ok{cb.SEP}{token}"},
        {"text": REFUSE, "callback_data": f"{cb.WEB_LOGIN}{cb.SEP}no{cb.SEP}{token}"},
    ]]})


def answer(
    ctx: BotContext, db: Session, chat_id: object, user_id: str, person: Person,
    message_id: int | None, rest: str | None,
) -> None:
    """The two buttons: `ok:<token>` approves, `no:<token>` refuses."""
    decision, _, token = (rest or "").partition(cb.SEP)
    if ctx.platform != Platform.TELEGRAM or decision not in ("ok", "no") or not _TOKEN.match(token):
        ctx.show(chat_id, EXPIRED, None, message_id)
        return
    if decision == "ok":
        ok = web_login.approve(db, token, person, user_id)
        ctx.show(chat_id, DONE if ok else EXPIRED, None, message_id)
    else:
        ok = web_login.deny(db, token)
        ctx.show(chat_id, REFUSED if ok else EXPIRED, None, message_id)
