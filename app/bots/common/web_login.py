"""«Log in with the bot»: the Telegram side of the web panel's sign-in.

The panel's link opens the bot with `/start wl_<token>`. The bot shows who is asking (device,
time, address) and two buttons; only the person pressing «تأیید» lets that browser in. The
refuse button and the details are the defence against someone sending a victim their own link.
"""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bots.common import callbacks as cb
from app.bots.common.context import BotContext
from app.core import clock
from app.core.jalali import format_jalali
from app.models import Person, Platform, WebCredential
from app.services import web_link, web_login

_TOKEN = re.compile(r"^[A-Za-z0-9_-]{16,64}$")

ASK = (
    "🔐 درخواست ورود به پنل وب\n\n"
    "کسی می‌خواهد با حساب تو وارد پنل GymCore شود:\n"
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

ASK_LINK = (
    "🔗 اتصال تلگرام به حساب وب\n\n"
    "حساب وب با نام کاربری «{username}» می‌خواهد به همین تلگرام وصل شود تا با «ورود با ربات» "
    "هم وارد شود:\n"
    "🖥 دستگاه: {device}\n"
    "🕒 زمان: {when}\n"
    "🌐 آدرس: {ip}\n\n"
    "فقط اگر خودت همین الان در سایت دکمهٔ «اتصال تلگرام» را زده‌ای تأیید کن."
)
CONFIRM_LINK = "✅ وصل کن"
LINKED = "✅ تلگرام به حساب وب وصل شد؛ از این به بعد با «ورود با ربات» هم وارد می‌شوی."
LINK_REFUSED = "❌ اتصال رد شد. اگر این درخواست مال تو نبود، کاری لازم نیست."
LINK_PROBLEM = {
    web_link.ALREADY: "این تلگرام از قبل به همین حساب وصل است.",
    web_link.REFUSED_STAFF: (
        "این تلگرام حساب مربی است. برای گذاشتن نام کاربری و گذرواژه، در سایت با «ورود با ربات» "
        "وارد شو و از بخش حساب بساز."
    ),
    web_link.REFUSED_HAS_WEB: "این تلگرام از قبل یک حساب وب با نام کاربری و گذرواژه دارد.",
    web_link.REFUSED_BOTH: (
        "هر دو حساب سابقه دارند (دوره یا پرداخت) و خودکار یکی نمی‌شوند. به مربی بگو تا یکی‌شان کند، "
        "یا در سایت با «ورود با ربات» وارد شو و همان‌جا نام کاربری بساز."
    ),
}


def token_from_start(text: str) -> str | None:
    """The token in `/start wl_<token>`, or None for any other message."""
    prefix = f"/start {web_login.START_PREFIX}"
    if not text.startswith(prefix):
        return None
    token = text[len(prefix):].strip()
    return token if _TOKEN.match(token) else ""


def link_token_from_start(text: str) -> str | None:
    """The token in `/start wk_<token>` (connect Telegram), or None for any other message."""
    prefix = f"/start {web_login.LINK_PREFIX}"
    if not text.startswith(prefix):
        return None
    token = text[len(prefix):].strip()
    return token if _TOKEN.match(token) else ""


def offer_link(ctx: BotContext, db: Session, chat_id: object, token: str) -> None:
    """Show «connect this Telegram to web account X» for a link the person just opened."""
    if ctx.platform != Platform.TELEGRAM:
        ctx.send(chat_id, TELEGRAM_ONLY)
        return
    request = web_login.pending_link(db, token) if token else None
    credential = (
        db.scalar(select(WebCredential).where(WebCredential.person_id == request.link_person_id))
        if request is not None else None
    )
    if request is None or credential is None:
        ctx.send(chat_id, EXPIRED)
        return
    now = clock.local_now()
    text = ASK_LINK.format(
        username=credential.username, device=web_login.describe_device(request.user_agent),
        when=f"{format_jalali(now.date())} {now:%H:%M}", ip=request.client_ip or "—",
    )
    ctx.send(chat_id, text, {"inline_keyboard": [[
        {"text": CONFIRM_LINK, "callback_data": f"{cb.WEB_LOGIN}{cb.SEP}lok{cb.SEP}{token}"},
        {"text": REFUSE, "callback_data": f"{cb.WEB_LOGIN}{cb.SEP}lno{cb.SEP}{token}"},
    ]]})


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
    if (
        ctx.platform != Platform.TELEGRAM
        or decision not in ("ok", "no", "lok", "lno")
        or not _TOKEN.match(token)
    ):
        ctx.show(chat_id, EXPIRED, None, message_id)
        return
    if decision in ("lok", "lno"):
        _answer_link(ctx, db, chat_id, user_id, person, message_id, decision == "lok", token)
        return
    if decision == "ok":
        ok = web_login.approve(db, token, person, user_id)
        ctx.show(chat_id, DONE if ok else EXPIRED, None, message_id)
    else:
        ok = web_login.deny(db, token)
        ctx.show(chat_id, REFUSED if ok else EXPIRED, None, message_id)


def _answer_link(
    ctx: BotContext, db: Session, chat_id: object, user_id: str, person: Person,
    message_id: int | None, accepted: bool, token: str,
) -> None:
    request = web_login.pending_link(db, token)
    if request is None:
        ctx.show(chat_id, EXPIRED, None, message_id)
        return
    request.status = web_login.CONSUMED  # one answer per request, either way
    db.commit()
    if not accepted:
        ctx.show(chat_id, LINK_REFUSED, None, message_id)
        return
    outcome = web_link.link(db, request.link_person_id, person, user_id)
    text = LINKED if outcome == web_link.LINKED else LINK_PROBLEM[outcome]
    ctx.show(chat_id, text, None, message_id)
