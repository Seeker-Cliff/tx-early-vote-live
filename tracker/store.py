"""CSV storage. Every file is append-only except daily_2026.csv (latest SOS values)."""
import csv
from pathlib import Path

from .config import DATA

LOG = DATA / "log.csv"                # accepted intraday readings
QUARANTINE = DATA / "quarantine.csv"  # rejected readings (intraday + daily), never shown as data
ATTEMPTS = DATA / "attempts.csv"      # every scheduled intraday attempt and its outcome
DAILY = DATA / "daily_2026.csv"       # accepted SOS daily values for 2026
HOURS = DATA / "hours.csv"

LOG_FIELDS = ["county", "scraped_at", "source_time", "day_n", "cum_in_person",
              "locations_reporting", "locations_total", "source_url"]
QUAR_FIELDS = ["tier", "county", "scraped_at", "source_time", "day_n", "cum_in_person",
               "locations_reporting", "locations_total", "reason", "source_url"]
ATTEMPT_FIELDS = ["county", "slot", "scraped_at", "status", "detail"]
DAILY_FIELDS = ["date", "day_n", "county", "registered_voters", "cum_in_person",
                "cum_mail", "fetched_at", "flag"]


def read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def append(path: Path, fields: list[str], row: dict) -> None:
    new = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in fields})


def write_all(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
