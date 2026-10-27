"""Program packages — bundles the coach builds once and sends to many students.

What a student sees is LIVE: the package's current items, so an item added or
edited later reaches everyone who has the package. A package that was ever sent
is never deleted — it is deactivated, which hides it from every student while
keeping who had it. Sending is idempotent, and each student is notified once,
when they get the package.

A file item holds one `file_id` per platform (a `file_id` only works on the
platform that issued it); `add_platform_copy` records the other platform's copy
when the coach sends the same file from the other bot.
"""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.copy import packages_texts as P
from app.core.exceptions import NotFoundError, ValidationError
from app.models import PackageAssignment, PackageItem, Person, Platform, ProgramPackage
from app.services import notifications

# How a file arrived through a bot, which picks its send method; "text" has none.
FILE_KINDS = ("document", "photo", "video")
ITEM_KINDS = (*FILE_KINDS, "text")

TITLE_LIMIT = 150
# The student's package screen is the title, the description and a hint — kept
# well under a message's 4096 characters.
DESCRIPTION_LIMIT = 3000
# Each item is one button on the student's screen and the coach's: well under the
# ~100-button keyboard ceiling, and the coach's item list stays one message.
MAX_ITEMS = 40
_LABEL_LIMIT = 40


# --- packages ---


def find(db: Session, package_id: int) -> ProgramPackage | None:
    return db.get(ProgramPackage, package_id)


def get(db: Session, package_id: int) -> ProgramPackage:
    package = find(db, package_id)
    if package is None:
        raise NotFoundError(P.NOT_FOUND)
    return package


def list_packages(db: Session, only_active: bool = False) -> list[ProgramPackage]:
    """Active packages first, newest first within each."""
    stmt = select(ProgramPackage).order_by(
        ProgramPackage.active.desc(), ProgramPackage.created_at.desc(), ProgramPackage.id.desc()
    )
    if only_active:
        stmt = stmt.where(ProgramPackage.active.is_(True))
    return list(db.scalars(stmt))


def check_title(title: str | None) -> str:
    """The cleaned title, or a ValidationError the coach can act on."""
    title = (title or "").strip()
    if not title:
        raise ValidationError(P.TITLE_REQUIRED)
    if len(title) > TITLE_LIMIT:
        raise ValidationError(P.TITLE_TOO_LONG.format(n=TITLE_LIMIT))
    return title


def _check_description(description: str | None) -> str | None:
    description = (description or "").strip()
    if len(description) > DESCRIPTION_LIMIT:
        raise ValidationError(P.DESCRIPTION_TOO_LONG.format(n=DESCRIPTION_LIMIT))
    return description or None


def create(
    db: Session, title: str, description: str | None = None, created_by: str | None = None
) -> ProgramPackage:
    package = ProgramPackage(
        title=check_title(title),
        description=_check_description(description),
        created_by=created_by,
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    return package


def update(
    db: Session, package_id: int, title: str | None = None, description: str | None = None
) -> ProgramPackage:
    """Rename and/or re-describe a package; an empty description clears it."""
    package = get(db, package_id)
    if title is not None:
        package.title = check_title(title)
    if description is not None:
        package.description = _check_description(description)
    db.commit()
    db.refresh(package)
    return package


def set_active(db: Session, package_id: int, active: bool) -> ProgramPackage:
    package = get(db, package_id)
    package.active = active
    db.commit()
    db.refresh(package)
    return package


def ever_assigned(db: Session, package_id: int) -> bool:
    return bool(db.scalar(
        select(func.count()).select_from(PackageAssignment)
        .where(PackageAssignment.package_id == package_id)
    ))


def delete(db: Session, package_id: int) -> None:
    """Delete a package and its items — refused once it was ever sent (deactivate it)."""
    package = get(db, package_id)
    if ever_assigned(db, package.id):
        raise ValidationError(P.DELETE_REFUSED)
    db.execute(sa_delete(PackageItem).where(PackageItem.package_id == package.id))
    db.delete(package)
    db.commit()


# --- items ---


def items(db: Session, package_id: int) -> list[PackageItem]:
    return list(db.scalars(
        select(PackageItem)
        .where(PackageItem.package_id == package_id)
        .order_by(PackageItem.sort_order, PackageItem.id)
    ))


def item_counts(db: Session, package_ids: Iterable[int]) -> dict[int, int]:
    ids = list(package_ids)
    counts = dict.fromkeys(ids, 0)
    if ids:
        rows = db.execute(
            select(PackageItem.package_id, func.count())
            .where(PackageItem.package_id.in_(ids))
            .group_by(PackageItem.package_id)
        )
        counts.update({package_id: count for package_id, count in rows})
    return counts


def find_item(db: Session, item_id: int) -> PackageItem | None:
    return db.get(PackageItem, item_id)


def get_item(db: Session, item_id: int) -> PackageItem:
    item = find_item(db, item_id)
    if item is None:
        raise NotFoundError(P.ITEM_NOT_FOUND)
    return item


def file_id_for(item: PackageItem, platform: Platform) -> str | None:
    """The item's file on this platform — a file_id from the other one is useless."""
    if platform == Platform.TELEGRAM:
        return item.telegram_file_id
    if platform == Platform.BALE:
        return item.bale_file_id
    return None


def _set_file_id(item: PackageItem, platform: Platform, file_id: str) -> None:
    if platform == Platform.TELEGRAM:
        item.telegram_file_id = file_id
    elif platform == Platform.BALE:
        item.bale_file_id = file_id
    else:
        raise ValueError(f"no bot file ids on {platform}")


def file_in_message(message: dict) -> tuple[str, str, str | None] | None:
    """(kind, file_id, file name) of the file a bot message carries, else None.

    An animation (GIF) arrives with a `document` as well, so it is kept as one;
    a photo comes in several sizes, the largest last.
    """
    document = message.get("document")
    if document and document.get("file_id"):
        return "document", document["file_id"], document.get("file_name")
    photos = message.get("photo")
    if photos and photos[-1].get("file_id"):
        return "photo", photos[-1]["file_id"], None
    video = message.get("video")
    if video and video.get("file_id"):
        return "video", video["file_id"], video.get("file_name")
    return None


def _check_item_title(title: str | None) -> str | None:
    title = (title or "").strip()
    if len(title) > TITLE_LIMIT:
        raise ValidationError(P.TITLE_TOO_LONG.format(n=TITLE_LIMIT))
    return title or None


def add_item(
    db: Session,
    package_id: int,
    kind: str,
    text: str | None = None,
    file_id: str | None = None,
    platform: Platform | None = None,
    original_filename: str | None = None,
    title: str | None = None,
) -> PackageItem:
    """Append an item: a file of `kind` from `platform`, or a text item."""
    package = get(db, package_id)
    if kind not in ITEM_KINDS:
        raise ValidationError(P.ITEM_KIND_INVALID)
    text = (text or "").strip() or None
    if kind == "text" and not text:
        raise ValidationError(P.ITEM_TEXT_REQUIRED)
    if kind != "text" and (not file_id or platform is None):
        raise ValidationError(P.FILE_REQUIRED)
    siblings = items(db, package.id)
    if len(siblings) >= MAX_ITEMS:
        raise ValidationError(P.ITEM_LIMIT.format(n=MAX_ITEMS))
    item = PackageItem(
        package_id=package.id,
        sort_order=max((s.sort_order for s in siblings), default=0) + 1,
        title=_check_item_title(title),
        kind=kind,
        text=text,
        original_filename=original_filename if kind != "text" else None,
    )
    if kind != "text":
        _set_file_id(item, platform, file_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def add_item_from_message(
    db: Session, package_id: int, message: dict, platform: Platform
) -> PackageItem:
    """An item from what the coach sent: a file — its caption becomes the item's
    text — or typed text. The file_id is recorded for the platform it came from."""
    found = file_in_message(message)
    if found is not None:
        kind, file_id, file_name = found
        return add_item(
            db, package_id, kind, text=message.get("caption"), file_id=file_id,
            platform=platform, original_filename=file_name,
        )
    text = (message.get("text") or "").strip()
    if not text:  # a sticker, a voice note, a location…
        raise ValidationError(P.ITEM_UNSUPPORTED)
    return add_item(db, package_id, "text", text=text)


def add_platform_copy(
    db: Session, item_id: int, message: dict, platform: Platform
) -> PackageItem:
    """Record `platform`'s copy of a file item, sent by the coach from that bot.

    It must be the same kind of file: the kind picks the one send method used
    on every platform.
    """
    item = get_item(db, item_id)
    if item.kind not in FILE_KINDS:
        raise ValidationError(P.ITEM_KIND_INVALID)
    found = file_in_message(message)
    if found is None:
        raise ValidationError(P.FILE_REQUIRED)
    kind, file_id, _ = found
    if kind != item.kind:
        raise ValidationError(P.COPY_WRONG_KIND.format(kind=P.KIND_NAMES[item.kind]))
    _set_file_id(item, platform, file_id)
    db.commit()
    db.refresh(item)
    return item


def update_item(
    db: Session, item_id: int, text: str | None = None, title: str | None = None
) -> PackageItem:
    """Change an item's text and/or title; an empty value clears it (a text item
    keeps its text — it is the item)."""
    item = get_item(db, item_id)
    if text is not None:
        text = text.strip()
        if not text and item.kind == "text":
            raise ValidationError(P.ITEM_TEXT_REQUIRED)
        item.text = text or None
    if title is not None:
        item.title = _check_item_title(title)
    db.commit()
    db.refresh(item)
    return item


def move_item(db: Session, item_id: int, direction: int) -> PackageItem:
    """Swap an item with its neighbour (direction -1 up, +1 down); the ends stay put."""
    item = get_item(db, item_id)
    siblings = items(db, item.package_id)
    for position, sibling in enumerate(siblings, start=1):  # dense, so a swap always moves
        sibling.sort_order = position
    index = next(i for i, sibling in enumerate(siblings) if sibling.id == item.id)
    target = index + (1 if direction > 0 else -1)
    if 0 <= target < len(siblings):
        other = siblings[target]
        item.sort_order, other.sort_order = other.sort_order, item.sort_order
    db.commit()
    return item


def delete_item(db: Session, item_id: int) -> int:
    """Remove an item from its package (and so from every student); returns the package id."""
    item = get_item(db, item_id)
    package_id = item.package_id
    db.delete(item)
    db.commit()
    return package_id


def item_icon(item: PackageItem) -> str:
    return P.KIND_ICONS.get(item.kind, P.KIND_ICONS["document"])


def item_label(item: PackageItem, limit: int = _LABEL_LIMIT) -> str:
    """The item's name on a button: the coach's title, else the first line of its
    text, else the file's name, else what kind of item it is."""
    first_line = next((line.strip() for line in (item.text or "").splitlines() if line.strip()), "")
    label = item.title or first_line or item.original_filename or P.KIND_NAMES.get(item.kind, "")
    return label if len(label) <= limit else f"{label[:limit - 1]}…"


def item_caption(item: PackageItem) -> str:
    """The item's words as the student gets them: the title on top, then the text."""
    return "\n\n".join(part for part in (item.title, item.text) if part)


# --- assignments ---


def get_assignment(db: Session, assignment_id: int) -> PackageAssignment:
    assignment = db.get(PackageAssignment, assignment_id)
    if assignment is None:
        raise NotFoundError(P.ASSIGNMENT_NOT_FOUND)
    return assignment


def active_person_ids(db: Session, package_id: int) -> set[int]:
    return set(db.scalars(
        select(PackageAssignment.person_id).where(
            PackageAssignment.package_id == package_id, PackageAssignment.active.is_(True)
        )
    ))


def recipient_counts(db: Session, package_ids: Iterable[int]) -> dict[int, int]:
    ids = list(package_ids)
    counts = dict.fromkeys(ids, 0)
    if ids:
        rows = db.execute(
            select(PackageAssignment.package_id, func.count())
            .where(PackageAssignment.package_id.in_(ids), PackageAssignment.active.is_(True))
            .group_by(PackageAssignment.package_id)
        )
        counts.update({package_id: count for package_id, count in rows})
    return counts


def recipients(db: Session, package_id: int) -> list[PackageAssignment]:
    """Who has the package now, by name."""
    return list(db.scalars(
        select(PackageAssignment)
        .join(Person, Person.id == PackageAssignment.person_id)
        .where(PackageAssignment.package_id == package_id, PackageAssignment.active.is_(True))
        .order_by(Person.name, Person.id)
    ))


def assign(
    db: Session,
    package_id: int,
    person_ids: Iterable[int],
    created_by: str | None = None,
    notify: bool = True,
) -> list[Person]:
    """Give the package to these students; returns the ones who did not have it.

    Idempotent: an already-active assignment is left alone, so sending again
    never duplicates a row or a message. A revoked one is switched back on. Each
    newly assigned student is notified once. An empty or inactive package is
    refused — the student would open nothing.
    """
    package = get(db, package_id)
    if not package.active:
        raise ValidationError(P.SEND_INACTIVE)
    if not item_counts(db, [package.id])[package.id]:
        raise ValidationError(P.SEND_EMPTY)
    wanted = list(dict.fromkeys(person_ids))
    if not wanted:
        return []
    people = {p.id: p for p in db.scalars(select(Person).where(Person.id.in_(wanted)))}
    existing = {
        a.person_id: a
        for a in db.scalars(select(PackageAssignment).where(
            PackageAssignment.package_id == package.id, PackageAssignment.person_id.in_(wanted)
        ))
    }
    newly: list[Person] = []
    for person_id in wanted:
        person = people.get(person_id)
        if person is None:  # deleted since the coach picked them
            continue
        assignment = existing.get(person_id)
        if assignment is None:
            db.add(PackageAssignment(
                package_id=package.id, person_id=person_id, created_by=created_by
            ))
        elif assignment.active:
            continue
        else:
            assignment.active = True
        newly.append(person)
    db.commit()
    if notify:
        text = P.NOTIFY_ASSIGNED.format(title=package.title)
        for person in newly:
            notifications.notify_person(db, person, text)
    return newly


def unassign(db: Session, assignment_id: int) -> PackageAssignment:
    """Take a student's access away; the row stays, so sending again restores it."""
    assignment = get_assignment(db, assignment_id)
    assignment.active = False
    db.commit()
    db.refresh(assignment)
    return assignment


def assignments_for_person(db: Session, person_id: int) -> list[PackageAssignment]:
    """The coach's view of one student's packages: every active assignment, the
    deactivated packages included (the student does not see those)."""
    return list(db.scalars(
        select(PackageAssignment)
        .where(PackageAssignment.person_id == person_id, PackageAssignment.active.is_(True))
        .order_by(PackageAssignment.created_at.desc(), PackageAssignment.id.desc())
    ))


def _open_stmt(person_id: int):
    return (
        select(ProgramPackage)
        .join(PackageAssignment, PackageAssignment.package_id == ProgramPackage.id)
        .where(
            PackageAssignment.person_id == person_id,
            PackageAssignment.active.is_(True),
            ProgramPackage.active.is_(True),
        )
    )


def list_for_person(db: Session, person_id: int) -> list[ProgramPackage]:
    """The packages a student can open — actively theirs, and active — newest first."""
    stmt = _open_stmt(person_id).order_by(
        PackageAssignment.created_at.desc(), PackageAssignment.id.desc()
    )
    return list(db.scalars(stmt))


def open_for(db: Session, package_id: int, person_id: int) -> ProgramPackage | None:
    """The package if this student may open it, else None — a foreign, revoked,
    deactivated or made-up id all look the same."""
    return db.scalar(_open_stmt(person_id).where(ProgramPackage.id == package_id))
