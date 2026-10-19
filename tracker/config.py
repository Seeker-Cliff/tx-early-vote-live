"""Shared constants: paths, election calendars, Day N mapping."""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
HIST = DATA / "history"
DOCS = ROOT / "docs"

CT = ZoneInfo("America/Chicago")

# Early voting Day 1 for each November general (all start on a Monday, 12 days).
DAY1 = {
    2026: date(2026, 10, 19),
    2024: date(2024, 10, 21),
    2022: date(2022, 10, 24),
    2018: date(2018, 10, 22),
}
EV_DAYS = 12
COMPARE_YEARS = [2024, 2022, 2018]

# SOS live feed (civixapps) election id for the 2026 November general.
SOS_ELECTION_ID = 53815


def now_ct() -> datetime:
    return datetime.now(timezone.utc).astimezone(CT)


def day_n(d: date, year: int = 2026) -> int | None:
    """1-based early-voting day number, or None outside the window."""
    n = (d - DAY1[year]).days + 1
    return n if 1 <= n <= EV_DAYS else None


def date_for_day(n: int, year: int) -> date:
    return DAY1[year] + timedelta(days=n - 1)


def iso(dt: datetime) -> str:
    return dt.astimezone(CT).isoformat(timespec="seconds")
