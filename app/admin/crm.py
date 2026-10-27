"""Admin section: «📇 پیگیری‌ها» — the coach's follow-ups.

The front page counts what is waiting: follow-ups due today or overdue
(⏰ امروز), students whose course ended without a new one (🔁 تمدید), and open
leads — people who asked about classes but never registered (🧲 سرنخ‌ها).

A student's notes timeline and follow-ups are reached from their profile too
(students.py). Both are input screens: whatever the coach types there is the
new note, or the topic of the follow-up whose date they tap next — the same
"stage it, then tap" pattern as a session note on the grid.

Every screen about one student or lead names them; every typed answer has a
way back; a result is a flash line on the screen it returns to; a stale tap
lands on an explained «⌛» screen instead of an error.

Callback data is ``a:crm:<action>:<args>`` (≤ 64 bytes). Screens reached from
more than one place carry an origin: ``t`` the today list, ``p`` the student's
profile, ``r`` their renewal screen.
"""

from __future__ import annotations

from datetime import date, timedelta

from app.admin import common
from app.admin import students as students_admin
from app.admin.common import AdminReq
from app.bots.common import callbacks as cb
from app.copy import admin_texts as A
from app.copy import crm_texts as C
from app.copy import texts
from app.core.exceptions import NotFoundError, ValidationError
from app.core.jalali import format_jalali
from app.models import OPEN_LEAD_STATUSES, FollowUp, Lead, LeadSource, LeadStatus, StudentType
from app.services import crm as crm_service
from app.services import persons as persons_service

_PER_PAGE = 8
_SHORTCUT_DAYS = tuple(C.SHORTCUT_LABELS)  # فردا · ۳ روز · یک هفته
_SNIPPET = 24  # characters of a note inside a button
_NOTES_BUDGET = 3000  # characters of timeline per screen (a message stops at 4096)
_LEAD_NOTE_SHOWN = 1200  # the latest part of a lead's notes on its screen
_STYLE_SELECTED = "success"  # green on Telegram; Bale strips it (the ✅ stays)

# Short codes in callback data (Telegram caps callback_data at 64 bytes).
_STATUS_CODES = {
    "N": LeadStatus.NEW,
    "C": LeadStatus.CONTACTED,
    "T": LeadStatus.TRIAL,
    "W": LeadStatus.WON,
    "L": LeadStatus.LOST,
}
_CODE_OF_STATUS = {status: code for code, status in _STATUS_CODES.items()}
_OPEN_TABS = (LeadStatus.NEW, LeadStatus.CONTACTED, LeadStatus.TRIAL)
_CLOSED_TABS = (LeadStatus.WON, LeadStatus.LOST)
_SOURCE_CODES = {
    "I": LeadSource.INSTAGRAM,
    "T": LeadSource.TELEGRAM,
    "R": LeadSource.REFERRAL,
    "W": LeadSource.WALK_IN,
    "S": LeadSource.WEBSITE,
    "O": LeadSource.OTHER,
}
_TYPE_CODES = {"I": StudentType.IN_PERSON, "O": StudentType.ONLINE}
_ORIGINS = ("t", "p", "r")


def handle_callback(req: AdminReq, args: str) -> None:
    action, _, rest = (args or "").partition(":")
    handler = _ACTIONS.get(action)
    if handler is None:
        _front(req)
        return
    try:
        handler(req, rest)
    except NotFoundError:  # the lead, follow-up or student is gone
        _expired(req)


def handle_message(req: AdminReq, message: dict, substep: str, state) -> None:
    text = (message.get("text") or "").strip()
    handler = _STEPS.get(substep)
    if handler is None or text.startswith("/"):  # a command is never an answer
        common.clear(req)
        _front(req)
        return
    try:
        handler(req, text, state.data)
    except NotFoundError:
        common.clear(req)
        _expired(req)


# --- small helpers ---


def _flashed(flash: str | None, body: str) -> str:
    return f"{flash}\n\n{body}" if flash else body


def _expired(req: AdminReq) -> None:
    common.render(req, C.EXPIRED, common.inline([
        [common.button(texts.BTN_ADMIN_CRM, "crm")],
        [common.home_button()],
    ]))


def _parts(rest: str) -> list[str]:
    return (rest or "").split(":")


def _int_at(parts: list[str], index: int) -> int | None:
    return cb.parse_int(parts[index] or None) if index < len(parts) else None


def _origin_at(parts: list[str], index: int, default: str) -> str:
    origin = parts[index] if index < len(parts) else default
    return origin if origin in _ORIGINS else default


def _page_of(rest: str) -> int:
    """The page a pager button asks for: it appends ``page:<n>``."""
    _, _, page = (rest or "").rpartition("page:")
    return common.parse_count(page) or 1


def _window(items: list, page: int) -> tuple[list, int, int]:
    pages = max((len(items) + _PER_PAGE - 1) // _PER_PAGE, 1)
    page = max(min(page, pages), 1)
    return items[(page - 1) * _PER_PAGE: page * _PER_PAGE], page, pages


def _pending(req: AdminReq, step: str) -> dict | None:
    """The in-progress data, if the chat is still at `step` — a tap on an older
    prompt's button is not."""
    state = req.store.get(req.ctx.platform, req.chat_id)
    return state.data if state is not None and state.step == step else None


def _snippet(text: str | None, limit: int = _SNIPPET) -> str:
    flat = " ".join((text or "").split())
    return flat if len(flat) <= limit else f"{flat[:limit]}{C.NOTE_CLIPPED}"


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else f"{text[:limit]}{C.NOTE_CLIPPED}"


def _when(day: date, today: date) -> str:
    """«امروز» · «فردا» · «🔴 ۳ روز گذشته» · or the Jalali date."""
    if day == today:
        return C.WHEN_TODAY
    if day < today:
        return C.WHEN_OVERDUE.format(n=(today - day).days)
    if day == today + timedelta(days=1):
        return C.WHEN_TOMORROW
    return format_jalali(day)


def _ago(days: int | None) -> str:
    if days is None:
        return C.NO_END_DATE
    return C.WHEN_TODAY if days == 0 else C.DAYS_AGO.format(n=days)


# --- front page ---


def _front(req: AdminReq, flash: str | None = None) -> None:
    summary = crm_service.summary(req.db)
    rows = [
        [common.button(C.BTN_TODAY.format(n=summary.due), "crm", "today")],
        [
            common.button(C.BTN_RENEWALS.format(n=summary.renewals), "crm", "ren"),
            common.button(C.BTN_LEADS.format(n=summary.leads), "crm", "leads"),
        ],
        [common.button(C.BTN_NEW_LEAD, "crm", "new")],
    ]
    common.render(req, _flashed(flash, f"{C.TITLE}\n{C.FRONT_HINT}"), common.with_back(rows))


# --- ⏰ today: follow-ups due today or overdue ---


def _cb_today(req: AdminReq, rest: str) -> None:
    _today(req, page=_page_of(rest))


def _today(req: AdminReq, page: int = 1, flash: str | None = None) -> None:
    today = crm_service.local_today()
    due = crm_service.list_due(req.db, today)
    window, page, pages = _window(due, page)
    rows = [[common.button(_due_label(f, today), "crm", "fu", f.id, "t")] for f in window]
    body = f"{C.TODAY_TITLE}\n{C.TODAY_HINT if due else C.TODAY_EMPTY}"
    common.render(
        req, _flashed(flash, body), common.pager(rows, page, pages, ("crm", "today"), ("crm",))
    )


def _due_label(follow_up: FollowUp, today: date) -> str:
    icon = "👤" if follow_up.person_id is not None else "🧲"
    label = (
        f"{icon} {crm_service.follow_up_target_name(follow_up)} · "
        f"{_when(follow_up.due_on, today)}"
    )
    return f"{label} · {_snippet(follow_up.note)}" if follow_up.note else label


# --- one follow-up: done / push back / open whoever it is about ---


def _cb_follow_up(req: AdminReq, rest: str) -> None:
    parts = _parts(rest)
    follow_up_id = _int_at(parts, 0)
    if follow_up_id is None:
        _expired(req)
        return
    _follow_up(req, follow_up_id, _origin_at(parts, 1, "t"))


def _follow_up(req: AdminReq, follow_up_id: int, origin: str, flash: str | None = None) -> None:
    follow_up = crm_service.get_follow_up(req.db, follow_up_id)
    today = crm_service.local_today()
    name = crm_service.follow_up_target_name(follow_up)
    due = f"📅 {C.LABEL_DUE}: {format_jalali(follow_up.due_on)}"
    if not follow_up.done:
        due = f"{due} ({_when(follow_up.due_on, today)})"
    lines = [C.FU_TITLE.format(name=name), "", due]
    if follow_up.note:
        lines.append(f"📝 {_clip(follow_up.note, 1000)}")
    if follow_up.lead is not None:
        lines.append(f"🧲 {C.LABEL_STATUS}: {C.STATUS_LABELS[follow_up.lead.status.value]}")
    rows: list[list[dict]] = []
    if follow_up.done:
        done_on = crm_service.local_date(follow_up.done_at) if follow_up.done_at else today
        lines.append(C.FU_IS_DONE.format(date=format_jalali(done_on)))
    else:
        lines += ["", C.FU_POSTPONE_HINT]
        rows.append([common.button(C.BTN_DONE, "crm", "done", follow_up.id, origin)])
        rows.append([
            common.button(C.SHORTCUT_LABELS[days], "crm", "pp", follow_up.id, days, origin)
            for days in _SHORTCUT_DAYS
        ])
    if follow_up.person_id is not None:
        rows.append([common.button(
            C.BTN_OPEN_STUDENT.format(name=name), "students", "view", follow_up.person_id
        )])
    else:
        rows.append([common.button(
            C.BTN_OPEN_LEAD.format(name=name), "crm", "lead", follow_up.lead_id
        )])
    common.render(
        req, _flashed(flash, "\n".join(lines)),
        common.with_back(rows, _follow_up_back(follow_up, origin)),
    )


def _follow_up_back(follow_up: FollowUp, origin: str) -> tuple:
    if origin in ("p", "r") and follow_up.person_id is not None:
        return ("crm", "pfu", follow_up.person_id, origin)
    return ("crm", "today")


def _after_follow_up(req: AdminReq, follow_up: FollowUp, origin: str, flash: str) -> None:
    """Back to the list the follow-up was opened from, with the result on top."""
    if origin in ("p", "r") and follow_up.person_id is not None:
        _person_follow_ups(req, follow_up.person_id, origin, flash=flash)
    else:
        _today(req, flash=flash)


def _cb_done(req: AdminReq, rest: str) -> None:
    parts = _parts(rest)
    follow_up_id = _int_at(parts, 0)
    if follow_up_id is None:
        _expired(req)
        return
    follow_up = crm_service.complete_follow_up(req.db, follow_up_id)
    flash = C.FU_DONE.format(name=crm_service.follow_up_target_name(follow_up))
    _after_follow_up(req, follow_up, _origin_at(parts, 1, "t"), flash)


def _cb_postpone(req: AdminReq, rest: str) -> None:
    parts = _parts(rest)
    follow_up_id, days = _int_at(parts, 0), _int_at(parts, 1)
    origin = _origin_at(parts, 2, "t")
    if follow_up_id is None or days not in _SHORTCUT_DAYS:
        _expired(req)
        return
    try:
        follow_up = crm_service.postpone_follow_up(req.db, follow_up_id, days)
    except ValidationError as exc:  # already done — an old screen
        _follow_up(req, follow_up_id, origin, flash=f"⚠️ {exc}")
        return
    flash = C.FU_MOVED.format(
        name=crm_service.follow_up_target_name(follow_up), date=format_jalali(follow_up.due_on)
    )
    _after_follow_up(req, follow_up, origin, flash)


# --- 🔁 renewals ---


def _cb_renewals(req: AdminReq, rest: str) -> None:
    _renewals(req, page=_page_of(rest))


def _renewals(req: AdminReq, page: int = 1, flash: str | None = None) -> None:
    candidates = crm_service.renewal_candidates(req.db)
    window, page, pages = _window(candidates, page)
    rows = []
    for candidate in window:
        mark = C.RENEWAL_FOLLOWED if candidate.followed_up else C.RENEWAL_WAITING
        rows.append([
            common.button(candidate.person.name, "crm", "rc", candidate.person.id),
            common.button(f"{mark} {_ago(candidate.days_since)}", "crm", "rc", candidate.person.id),
        ])
    body = f"{C.RENEWALS_TITLE}\n{C.RENEWALS_HINT if candidates else C.RENEWALS_EMPTY}"
    common.render(
        req, _flashed(flash, body), common.pager(rows, page, pages, ("crm", "ren"), ("crm",))
    )


def _cb_candidate(req: AdminReq, rest: str) -> None:
    person_id = _int_at(_parts(rest), 0)
    if person_id is None:
        _expired(req)
        return
    _candidate(req, person_id)


def _candidate(req: AdminReq, person_id: int, flash: str | None = None) -> None:
    """One student to call about renewing: their course, when it ended, and
    what has been said since."""
    person = persons_service.get(req.db, person_id)
    candidate = crm_service.renewal_candidate(req.db, person_id)
    if candidate is None:  # renewed (or got a new course) meanwhile
        _renewals(req, flash=C.NOT_A_CANDIDATE.format(name=person.name))
        return
    title = candidate.course.class_type.title
    lines = [C.CANDIDATE_TITLE.format(name=person.name), ""]
    if candidate.ended_on is not None:
        lines.append(C.CANDIDATE_COURSE.format(
            title=title, date=format_jalali(candidate.ended_on), ago=_ago(candidate.days_since)
        ))
    else:
        lines.append(C.CANDIDATE_COURSE_NO_DATE.format(title=title))
    if person.phone:
        lines.append(f"📞 {C.LABEL_PHONE}: {person.phone}")
    lines.append(C.CANDIDATE_FOLLOWED if candidate.followed_up else C.CANDIDATE_WAITING)
    latest = crm_service.list_notes(req.db, person_id, limit=1)
    if latest:
        lines.append(f"📝 {C.LABEL_LAST_NOTE}: {_snippet(latest[0].text, 200)}")
    upcoming = crm_service.open_follow_ups(req.db, person_id)
    if upcoming:
        lines.append(f"⏰ {C.LABEL_NEXT_FOLLOW_UP}: {format_jalali(upcoming[0].due_on)}")
    rows = [
        [
            common.button(C.BTN_PROFILE, "students", "view", person_id),
            common.button(C.BTN_RENEW, "courses", "renew", candidate.course.id),
        ],
        [
            common.button(C.BTN_NOTE, "crm", "notes", person_id, "r"),
            common.button(C.BTN_FOLLOW_UP, "crm", "pfu", person_id, "r"),
        ],
    ]
    common.render(req, _flashed(flash, "\n".join(lines)), common.with_back(rows, ("crm", "ren")))


def _person_back(person_id: int, origin: str) -> tuple:
    return ("crm", "rc", person_id) if origin == "r" else ("students", "view", person_id)


# --- 📝 a student's notes timeline (type to add) ---


def _cb_notes(req: AdminReq, rest: str) -> None:
    parts = _parts(rest)
    person_id = _int_at(parts, 0)
    if person_id is None:
        _expired(req)
        return
    _notes(req, person_id, _origin_at(parts, 1, "p"))


def _notes(req: AdminReq, person_id: int, origin: str, flash: str | None = None) -> None:
    """Newest first, as many as fit on one screen; typing adds the next one."""
    person = persons_service.get(req.db, person_id)
    notes = crm_service.list_notes(req.db, person_id)
    lines = [C.NOTES_TITLE.format(name=person.name), ""]
    if not notes:
        lines += [C.NOTES_EMPTY, ""]
    used = shown = 0
    for note in notes:
        entry = C.NOTE_ENTRY.format(
            date=format_jalali(crm_service.local_date(note.created_at)),
            text=_clip(note.text, _NOTES_BUDGET),
        )
        if shown and used + len(entry) > _NOTES_BUDGET:
            break
        lines += [entry, ""]
        used += len(entry)
        shown += 1
    if shown < len(notes):
        lines += [C.NOTES_OLDER.format(n=len(notes) - shown), ""]
    lines.append(C.NOTES_HINT)
    common.prompt_show(
        req, _flashed(flash, "\n".join(lines)), "crm:note", {"pid": person_id, "o": origin},
        keyboard=common.with_back([], _person_back(person_id, origin)),
    )


def _msg_note(req: AdminReq, text: str, data: dict) -> None:
    person_id, origin = data.get("pid"), data.get("o", "p")
    if not person_id:
        _expired(req)
        return
    if not text:  # a photo or a sticker
        _notes(req, person_id, origin, flash=C.NEEDS_TEXT)
        return
    crm_service.add_note(req.db, person_id, text, created_by=req.user_id)
    _notes(req, person_id, origin, flash=C.NOTE_SAVED)


# --- ⏰ a student's follow-ups (type a topic, tap a date) ---


def _cb_person_follow_ups(req: AdminReq, rest: str) -> None:
    parts = _parts(rest)
    person_id = _int_at(parts, 0)
    if person_id is None:
        _expired(req)
        return
    _person_follow_ups(req, person_id, _origin_at(parts, 1, "p"))


def _person_follow_ups(
    req: AdminReq,
    person_id: int,
    origin: str,
    flash: str | None = None,
    staged: str | None = None,
) -> None:
    person = persons_service.get(req.db, person_id)
    today = crm_service.local_today()
    pending = crm_service.open_follow_ups(req.db, person_id)
    lines = [C.PFU_TITLE.format(name=person.name)]
    if not pending:
        lines += ["", C.PFU_NONE]
    rows = [
        [common.button(_open_label(f, today), "crm", "fu", f.id, origin)]
        for f in pending[:_PER_PAGE]
    ]
    if staged:
        lines += ["", C.PFU_STAGED.format(note=_clip(staged, 500))]
    lines += ["", C.PFU_HINT]
    rows.append([
        common.button(C.SHORTCUT_LABELS[days], "crm", "pfa", person_id, days, origin)
        for days in _SHORTCUT_DAYS
    ])
    rows.append([common.button(C.BTN_OTHER_DATE, "crm", "pfd", person_id, origin)])
    common.prompt_show(
        req, _flashed(flash, "\n".join(lines)), "crm:pfu",
        {"pid": person_id, "o": origin, "note": staged},
        keyboard=common.with_back(rows, _person_back(person_id, origin)),
    )


def _open_label(follow_up: FollowUp, today: date) -> str:
    when = _when(follow_up.due_on, today)
    label = when if follow_up.due_on < today else f"⏰ {when}"  # overdue already reads 🔴
    return f"{label} · {_snippet(follow_up.note)}" if follow_up.note else label


def _staged_note(req: AdminReq, person_id: int) -> str | None:
    """The topic typed on this student's follow-up screen, waiting for a date."""
    state = req.store.get(req.ctx.platform, req.chat_id)
    if state is None or state.step not in ("crm:pfu", "crm:pfdate"):
        return None
    return state.data.get("note") if state.data.get("pid") == person_id else None


def _msg_stage(req: AdminReq, text: str, data: dict) -> None:
    person_id, origin = data.get("pid"), data.get("o", "p")
    if not person_id:
        _expired(req)
        return
    if not text:
        _person_follow_ups(req, person_id, origin, flash=C.NEEDS_TEXT, staged=data.get("note"))
        return
    _person_follow_ups(req, person_id, origin, staged=text)


def _cb_person_follow_up_add(req: AdminReq, rest: str) -> None:
    parts = _parts(rest)
    person_id, days = _int_at(parts, 0), _int_at(parts, 1)
    if person_id is None or days not in _SHORTCUT_DAYS:
        _expired(req)
        return
    today = crm_service.local_today()
    _add_person_follow_up(
        req, person_id, _origin_at(parts, 2, "p"), today + timedelta(days=days), today
    )


def _add_person_follow_up(
    req: AdminReq, person_id: int, origin: str, due_on: date, today: date
) -> None:
    crm_service.add_follow_up(
        req.db, due_on, person_id=person_id, note=_staged_note(req, person_id),
        created_by=req.user_id, today=today,
    )
    _person_follow_ups(req, person_id, origin, flash=C.FU_SAVED.format(date=format_jalali(due_on)))


def _cb_person_follow_up_date(req: AdminReq, rest: str) -> None:
    parts = _parts(rest)
    person_id = _int_at(parts, 0)
    if person_id is None:
        _expired(req)
        return
    persons_service.get(req.db, person_id)
    origin = _origin_at(parts, 1, "p")
    data = {"pid": person_id, "o": origin, "note": _staged_note(req, person_id)}
    _ask_person_date(req, data)


def _ask_person_date(req: AdminReq, data: dict, warning: str | None = None) -> None:
    common.prompt(
        req, f"{warning}\n{C.ASK_DATE}" if warning else C.ASK_DATE, "crm:pfdate", data,
        keyboard=common.cancel_keyboard(("crm", "pfu", data["pid"], data["o"])),
    )


def _msg_person_date(req: AdminReq, text: str, data: dict) -> None:
    person_id = data.get("pid")
    if not person_id:
        _expired(req)
        return
    today = crm_service.local_today()
    due_on = common.parse_date(text)
    if due_on is None:
        _ask_person_date(req, data, warning=C.INVALID_DATE)
        return
    try:
        crm_service.check_due(due_on, today)
    except ValidationError as exc:
        _ask_person_date(req, data, warning=f"⚠️ {exc}")
        return
    _add_person_follow_up(req, person_id, data.get("o", "p"), due_on, today)


# --- 🧲 leads ---


def _cb_leads(req: AdminReq, rest: str) -> None:
    code, _, _ = (rest or "").partition(":")
    _leads(req, _STATUS_CODES.get(code), page=_page_of(rest))


def _leads(
    req: AdminReq,
    status: LeadStatus | None = None,
    page: int = 1,
    flash: str | None = None,
) -> None:
    """One status tab of the leads. With no tab given, the first open one that
    has anyone in it."""
    counts = crm_service.lead_counts(req.db)
    if status is None:
        status = next((s for s in _OPEN_TABS if counts[s]), LeadStatus.NEW)
    leads = crm_service.list_leads(req.db, status)
    window, page, pages = _window(leads, page)
    today = crm_service.local_today()

    def tab(kind: LeadStatus) -> dict:
        label = f"{C.STATUS_LABELS[kind.value]} ({counts[kind]})"
        selected = kind == status
        return common.button(
            A.TAB_SELECTED.format(label=label) if selected else label,
            "crm", "leads", _CODE_OF_STATUS[kind],
            style=_STYLE_SELECTED if selected else None,
        )

    top = [
        [tab(kind) for kind in _OPEN_TABS],
        [tab(kind) for kind in _CLOSED_TABS],
        [common.button(C.BTN_NEW_LEAD, "crm", "new")],
    ]
    items = [
        [
            common.button(lead.name, "crm", "lead", lead.id),
            common.button(_lead_label(lead, today), "crm", "lead", lead.id),
        ]
        for lead in window
    ]
    body = (
        f"{C.LEADS_TITLE} — {C.STATUS_LABELS[status.value]}\n"
        f"{C.LEADS_HINT if leads else C.LEADS_EMPTY}"
    )
    base = ("crm", "leads", _CODE_OF_STATUS[status])
    keyboard = common.pager(top + items, page, pages, base, ("crm",))
    common.render(req, _flashed(flash, body), keyboard)


def _lead_label(lead: Lead, today: date) -> str:
    if crm_service.is_converted(lead):
        return f"👤 {lead.person.name}"
    if lead.next_follow_up is not None:
        return f"⏰ {_when(lead.next_follow_up, today)}"
    return C.SOURCE_LABELS[lead.source.value]


def _cb_lead(req: AdminReq, rest: str) -> None:
    lead_id = _int_at(_parts(rest), 0)
    if lead_id is None:
        _expired(req)
        return
    _lead(req, lead_id)


def _lead(req: AdminReq, lead_id: int, flash: str | None = None) -> None:
    lead = crm_service.get_lead(req.db, lead_id)
    today = crm_service.local_today()
    converted = crm_service.is_converted(lead)
    lines = [
        C.LEAD_TITLE.format(name=lead.name),
        "",
        f"📌 {C.LABEL_STATUS}: {C.STATUS_LABELS[lead.status.value]}",
        f"📞 {C.LABEL_PHONE}: {lead.phone or '-'}",
        f"🧭 {C.LABEL_SOURCE}: {C.SOURCE_LABELS[lead.source.value]}",
    ]
    if lead.interest:
        lines.append(f"🎯 {C.LABEL_INTEREST}: {lead.interest}")
    lines.append(f"🗓 {C.LABEL_CREATED}: {format_jalali(crm_service.local_date(lead.created_at))}")
    if lead.next_follow_up is not None:
        lines.append(
            f"⏰ {C.LABEL_NEXT_FOLLOW_UP}: {format_jalali(lead.next_follow_up)} "
            f"({_when(lead.next_follow_up, today)})"
        )
    if lead.note:
        note = lead.note
        if len(note) > _LEAD_NOTE_SHOWN:  # the latest lines are the ones that matter
            note = f"{C.NOTE_CLIPPED}{note[-_LEAD_NOTE_SHOWN:]}"
        lines += ["", f"📝 {C.LABEL_NOTE}:", note]

    rows: list[list[dict]] = []
    if converted:
        lines += ["", C.LEAD_WON.format(name=lead.person.name)]
        rows.append([common.button(
            C.BTN_OPEN_STUDENT.format(name=lead.person.name), "students", "view", lead.person_id
        )])
    else:
        known = crm_service.person_with_phone(req.db, lead.phone)
        if known is not None:
            lines += ["", C.LEAD_PHONE_KNOWN.format(name=known.name)]
        rows.append([_status_button(lead, kind) for kind in _OPEN_TABS])
        rows.append([
            common.button(C.BTN_LEAD_NOTE, "crm", "lnote", lead.id),
            common.button(C.BTN_LEAD_PHONE, "crm", "lphone", lead.id),
        ])
        if lead.status in OPEN_LEAD_STATUSES:
            lines += ["", C.LEAD_FOLLOW_UP_HINT]
            rows.append([
                common.button(f"⏰ {C.SHORTCUT_LABELS[days]}", "crm", "lfa", lead.id, days)
                for days in _SHORTCUT_DAYS
            ])
            follow = [common.button(C.BTN_OTHER_DATE, "crm", "lfd", lead.id)]
            if lead.next_follow_up is not None:
                follow.append(common.button(C.BTN_LEAD_FOLLOW_UP_DONE, "crm", "ldone", lead.id))
            rows.append(follow)
        last = [common.button(C.BTN_CONVERT, "crm", "conv", lead.id)]
        if lead.status != LeadStatus.LOST:
            last.append(common.button(C.BTN_LOST, "crm", "st", lead.id, "L"))
        rows.append(last)
    rows.append([common.button(C.BTN_DELETE_LEAD, "crm", "ldel", lead.id)])
    common.render(
        req, _flashed(flash, "\n".join(lines)),
        common.with_back(rows, ("crm", "leads", _CODE_OF_STATUS[lead.status])),
    )


def _status_button(lead: Lead, kind: LeadStatus) -> dict:
    label = C.STATUS_LABELS[kind.value]
    selected = lead.status == kind
    return common.button(
        A.TAB_SELECTED.format(label=label) if selected else label,
        "crm", "st", lead.id, _CODE_OF_STATUS[kind],
        style=_STYLE_SELECTED if selected else None,
    )


def _cb_status(req: AdminReq, rest: str) -> None:
    parts = _parts(rest)
    lead_id = _int_at(parts, 0)
    status = _STATUS_CODES.get(parts[1] if len(parts) > 1 else "")
    if lead_id is None or status is None or status == LeadStatus.WON:
        _expired(req)
        return
    try:
        lead = crm_service.set_lead_status(req.db, lead_id, status)
    except ValidationError as exc:
        _lead(req, lead_id, flash=f"⚠️ {exc}")
        return
    if status == LeadStatus.LOST:
        flash = C.LEAD_LOST.format(name=lead.name)
    else:
        flash = C.STATUS_SAVED.format(status=C.STATUS_LABELS[status.value])
    _lead(req, lead_id, flash=flash)


def _lead_from(req: AdminReq, rest: str) -> Lead | None:
    """The lead a callback names, or None (after showing ⌛) when it is garbled."""
    lead_id = _int_at(_parts(rest), 0)
    if lead_id is None:
        _expired(req)
        return None
    return crm_service.get_lead(req.db, lead_id)


def _cb_lead_note(req: AdminReq, rest: str) -> None:
    lead = _lead_from(req, rest)
    if lead is not None:
        _ask_lead_note(req, lead)


def _ask_lead_note(req: AdminReq, lead: Lead, warning: str | None = None) -> None:
    ask = C.ASK_LEAD_NOTE.format(name=lead.name)
    common.prompt(
        req, f"{warning}\n{ask}" if warning else ask, "crm:lnote", {"lid": lead.id},
        keyboard=common.cancel_keyboard(("crm", "lead", lead.id)),
    )


def _msg_lead_note(req: AdminReq, text: str, data: dict) -> None:
    lead = crm_service.get_lead(req.db, data.get("lid") or 0)
    if not text:
        _ask_lead_note(req, lead, warning=C.NEEDS_TEXT)
        return
    crm_service.add_lead_note(req.db, lead.id, text)
    _lead(req, lead.id, flash=C.NOTE_SAVED)


def _cb_lead_phone(req: AdminReq, rest: str) -> None:
    lead = _lead_from(req, rest)
    if lead is not None:
        _ask_lead_phone(req, lead)


def _ask_lead_phone(req: AdminReq, lead: Lead, warning: str | None = None) -> None:
    template = C.ASK_LEAD_PHONE_EDIT_CLEAR if lead.phone else C.ASK_LEAD_PHONE_EDIT
    ask = template.format(name=lead.name)
    shortcuts = [[common.button(C.BTN_CLEAR_PHONE, "crm", "lphclr", lead.id)]] if lead.phone else []
    common.prompt(
        req, f"{warning}\n{ask}" if warning else ask, "crm:lphone", {"lid": lead.id},
        keyboard=common.cancel_keyboard(("crm", "lead", lead.id), rows=shortcuts),
    )


def _msg_lead_phone(req: AdminReq, text: str, data: dict) -> None:
    lead = crm_service.get_lead(req.db, data.get("lid") or 0)
    if not text:  # clearing is the «➖ حذف شماره» button, never an empty message
        _ask_lead_phone(req, lead, warning=C.NEEDS_TEXT)
        return
    try:
        crm_service.set_lead_phone(req.db, lead.id, text)
    except ValidationError as exc:
        _ask_lead_phone(req, lead, warning=f"⚠️ {exc}")
        return
    _lead(req, lead.id, flash=C.PHONE_SAVED)


def _cb_lead_phone_clear(req: AdminReq, rest: str) -> None:
    lead = _lead_from(req, rest)
    if lead is not None:
        crm_service.set_lead_phone(req.db, lead.id, None)
        _lead(req, lead.id, flash=C.PHONE_CLEARED)


def _cb_lead_follow_up(req: AdminReq, rest: str) -> None:
    parts = _parts(rest)
    lead_id, days = _int_at(parts, 0), _int_at(parts, 1)
    if lead_id is None or days not in _SHORTCUT_DAYS:
        _expired(req)
        return
    today = crm_service.local_today()
    _set_lead_follow_up(req, lead_id, today + timedelta(days=days), today)


def _set_lead_follow_up(req: AdminReq, lead_id: int, due_on: date, today: date) -> None:
    try:
        crm_service.set_lead_follow_up(
            req.db, lead_id, due_on, today=today, created_by=req.user_id
        )
    except ValidationError as exc:  # the lead was closed meanwhile
        _lead(req, lead_id, flash=f"⚠️ {exc}")
        return
    _lead(req, lead_id, flash=C.FU_SAVED.format(date=format_jalali(due_on)))


def _cb_lead_follow_up_date(req: AdminReq, rest: str) -> None:
    lead = _lead_from(req, rest)
    if lead is not None:
        _ask_lead_date(req, lead.id)


def _ask_lead_date(req: AdminReq, lead_id: int, warning: str | None = None) -> None:
    common.prompt(
        req, f"{warning}\n{C.ASK_DATE}" if warning else C.ASK_DATE, "crm:lfdate",
        {"lid": lead_id}, keyboard=common.cancel_keyboard(("crm", "lead", lead_id)),
    )


def _msg_lead_date(req: AdminReq, text: str, data: dict) -> None:
    lead = crm_service.get_lead(req.db, data.get("lid") or 0)
    today = crm_service.local_today()
    due_on = common.parse_date(text)
    if due_on is None:
        _ask_lead_date(req, lead.id, warning=C.INVALID_DATE)
        return
    try:
        crm_service.check_due(due_on, today)
    except ValidationError as exc:
        _ask_lead_date(req, lead.id, warning=f"⚠️ {exc}")
        return
    _set_lead_follow_up(req, lead.id, due_on, today)


def _cb_lead_follow_up_done(req: AdminReq, rest: str) -> None:
    lead = _lead_from(req, rest)
    if lead is None:
        return
    follow_up = crm_service.open_lead_follow_up(lead)
    if follow_up is None:  # an old screen: it was done already
        _lead(req, lead.id, flash=f"⚠️ {C.ERR_FOLLOW_UP_DONE}")
        return
    crm_service.complete_follow_up(req.db, follow_up.id)
    _lead(req, lead.id, flash=C.LEAD_FOLLOW_UP_DONE.format(name=lead.name))


def _cb_convert(req: AdminReq, rest: str) -> None:
    """«✅ تبدیل به شاگرد» asks first — and whether they train حضوری or غیرحضوری."""
    lead = _lead_from(req, rest)
    if lead is None:
        return
    if crm_service.is_converted(lead):
        _lead(req, lead.id)
        return
    rows = [
        [
            common.button(A.TYPE_LABELS[StudentType.IN_PERSON.value], "crm", "cgo", lead.id, "I"),
            common.button(A.TYPE_LABELS[StudentType.ONLINE.value], "crm", "cgo", lead.id, "O"),
        ],
        [common.button(A.CANCEL, "crm", "lead", lead.id, style="danger")],
    ]
    common.render(req, C.CONFIRM_CONVERT.format(name=lead.name), common.inline(rows))


def _cb_convert_go(req: AdminReq, rest: str) -> None:
    parts = _parts(rest)
    lead_id = _int_at(parts, 0)
    kind = _TYPE_CODES.get(parts[1] if len(parts) > 1 else "")
    if lead_id is None or kind is None:
        _expired(req)
        return
    result = crm_service.convert_lead(req.db, lead_id, student_type=kind, created_by=req.user_id)
    template = C.CONVERT_LINKED if result.linked else C.CONVERTED
    students_admin._profile(req, result.person.id, flash=template.format(name=result.person.name))


def _cb_delete_lead(req: AdminReq, rest: str) -> None:
    lead = _lead_from(req, rest)
    if lead is None:
        return
    common.render(req, C.CONFIRM_DELETE_LEAD.format(name=lead.name), common.inline([[
        common.button(A.BTN_YES_DELETE, "crm", "ldelgo", lead.id),
        common.button(A.CANCEL, "crm", "lead", lead.id),
    ]]))


def _cb_delete_lead_go(req: AdminReq, rest: str) -> None:
    lead = _lead_from(req, rest)
    if lead is None:
        return
    name, status = lead.name, lead.status
    crm_service.delete_lead(req.db, lead.id)
    _leads(req, status, flash=C.LEAD_DELETED.format(name=name))


# --- ➕ a new lead: name → phone (⏭) → source → interest (⏭) ---


def _cb_new(req: AdminReq, rest: str) -> None:
    _ask_new_name(req)


def _ask_new_name(req: AdminReq, warning: str | None = None) -> None:
    common.prompt(
        req, f"{warning}\n{C.ASK_LEAD_NAME}" if warning else C.ASK_LEAD_NAME, "crm:nname", {},
        keyboard=common.cancel_keyboard(("crm",)),
    )


def _msg_new_name(req: AdminReq, text: str, data: dict) -> None:
    try:
        name = crm_service.clean_name(text)
    except ValidationError as exc:
        _ask_new_name(req, warning=f"⚠️ {exc}")
        return
    _ask_new_phone(req, {"name": name})


def _ask_new_phone(req: AdminReq, data: dict, warning: str | None = None) -> None:
    common.prompt(
        req, f"{warning}\n{C.ASK_LEAD_PHONE}" if warning else C.ASK_LEAD_PHONE, "crm:nphone",
        data, keyboard=common.cancel_keyboard(
            ("crm",), rows=[[common.button(A.SKIP, "crm", "nskp")]]
        ),
    )


def _msg_new_phone(req: AdminReq, text: str, data: dict) -> None:
    if not text:
        _ask_new_phone(req, data, warning=C.NEEDS_TEXT)
        return
    try:
        data["phone"] = crm_service.clean_phone(text)
    except ValidationError as exc:
        _ask_new_phone(req, data, warning=f"⚠️ {exc}")
        return
    _ask_new_source(req, data)


def _cb_new_skip_phone(req: AdminReq, rest: str) -> None:
    data = _pending(req, "crm:nphone")
    if data is None:
        _expired(req)
        return
    data["phone"] = None
    _ask_new_source(req, data)


def _ask_new_source(req: AdminReq, data: dict) -> None:
    buttons = [
        common.button(C.SOURCE_LABELS[source.value], "crm", "src", code)
        for code, source in _SOURCE_CODES.items()
    ]
    rows = [buttons[i: i + 2] for i in range(0, len(buttons), 2)]
    common.prompt_show(
        req, C.ASK_LEAD_SOURCE.format(name=data.get("name", "")), "crm:nsrc", data,
        keyboard=common.cancel_keyboard(("crm",), rows=rows),
    )


def _msg_new_source(req: AdminReq, text: str, data: dict) -> None:
    _ask_new_source(req, data)  # typed text while picking: show the buttons again


def _cb_new_source(req: AdminReq, rest: str) -> None:
    data = _pending(req, "crm:nsrc")
    code = _parts(rest)[0]
    if data is None or code not in _SOURCE_CODES:
        _expired(req)
        return
    data["source"] = code
    _ask_new_interest(req, data)


def _ask_new_interest(req: AdminReq, data: dict, warning: str | None = None) -> None:
    common.prompt(
        req, f"{warning}\n{C.ASK_LEAD_INTEREST}" if warning else C.ASK_LEAD_INTEREST,
        "crm:nint", data, keyboard=common.cancel_keyboard(
            ("crm",), rows=[[common.button(A.SKIP, "crm", "nski")]]
        ),
    )


def _msg_new_interest(req: AdminReq, text: str, data: dict) -> None:
    if not text:  # a photo or a sticker is not an answer; «⏭ رد کردن» skips
        _ask_new_interest(req, data, warning=C.NEEDS_TEXT)
        return
    try:
        interest = crm_service.clean_interest(text)
    except ValidationError as exc:
        _ask_new_interest(req, data, warning=f"⚠️ {exc}")
        return
    _create_lead(req, data, interest)


def _cb_new_skip_interest(req: AdminReq, rest: str) -> None:
    data = _pending(req, "crm:nint")
    if data is None:
        _expired(req)
        return
    _create_lead(req, data, None)


def _create_lead(req: AdminReq, data: dict, interest: str | None) -> None:
    if not data.get("name"):
        _expired(req)
        return
    lead = crm_service.create_lead(
        req.db,
        name=data["name"],
        phone=data.get("phone"),
        source=_SOURCE_CODES.get(data.get("source") or "", LeadSource.OTHER),
        interest=interest,
        created_by=req.user_id,
    )
    common.clear(req)
    _lead(req, lead.id, flash=C.LEAD_SAVED)


# --- routing tables (after the handlers they name) ---

_ACTIONS = {
    "home": lambda req, rest: _front(req),
    "today": _cb_today,
    "fu": _cb_follow_up,
    "done": _cb_done,
    "pp": _cb_postpone,
    "ren": _cb_renewals,
    "rc": _cb_candidate,
    "notes": _cb_notes,
    "pfu": _cb_person_follow_ups,
    "pfa": _cb_person_follow_up_add,
    "pfd": _cb_person_follow_up_date,
    "leads": _cb_leads,
    "lead": _cb_lead,
    "st": _cb_status,
    "lnote": _cb_lead_note,
    "lphone": _cb_lead_phone,
    "lphclr": _cb_lead_phone_clear,
    "lfa": _cb_lead_follow_up,
    "lfd": _cb_lead_follow_up_date,
    "ldone": _cb_lead_follow_up_done,
    "conv": _cb_convert,
    "cgo": _cb_convert_go,
    "ldel": _cb_delete_lead,
    "ldelgo": _cb_delete_lead_go,
    "new": _cb_new,
    "nskp": _cb_new_skip_phone,
    "src": _cb_new_source,
    "nski": _cb_new_skip_interest,
}

_STEPS = {
    "note": _msg_note,
    "pfu": _msg_stage,
    "pfdate": _msg_person_date,
    "lnote": _msg_lead_note,
    "lphone": _msg_lead_phone,
    "lfdate": _msg_lead_date,
    "nname": _msg_new_name,
    "nphone": _msg_new_phone,
    "nsrc": _msg_new_source,
    "nint": _msg_new_interest,
}
