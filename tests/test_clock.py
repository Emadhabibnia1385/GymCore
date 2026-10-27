"""The coach's day is Tehran's, whatever clock the server keeps (production is UTC)."""

from datetime import UTC, date, datetime

from app.core import clock
from tests.fakes import callback_update, last_text, make_dispatcher


def test_after_midnight_in_tehran_it_is_already_tomorrow():
    # 21:00 UTC on 29 Sep is 00:30 on 30 Sep in Tehran.
    assert clock.today(datetime(2026, 9, 29, 21, 0, tzinfo=UTC)) == date(2026, 9, 30)
    # A naive timestamp — how SQLite stores CURRENT_TIMESTAMP — is read as UTC.
    assert clock.local_date(datetime(2026, 9, 29, 21, 0)) == date(2026, 9, 30)


def test_before_midnight_the_day_is_the_same():
    assert clock.today(datetime(2026, 9, 29, 20, 0, tzinfo=UTC)) == date(2026, 9, 29)


def test_the_attendance_day_view_opens_on_the_coachs_day(db, monkeypatch):
    monkeypatch.setattr(clock, "today", lambda now=None: date(2026, 9, 30))
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, 900, 111, "a:attend:today"))
    assert "1405/07/08" in last_text(client)  # 2026-09-30, not the server's day
