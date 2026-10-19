"""Tier 2 intraday scrapers. Each module exposes NAME and fetch() -> Reading.

To add a county: write tracker/counties/<name>.py, add it to SCRAPERS, add its hours
to data/hours.csv, and test it live with:  python -m tracker.run intraday --force <NAME>
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Reading:
    cum_in_person: int
    source_time: datetime          # when the county last updated its numbers
    source_url: str
    locations_reporting: int | None = None
    locations_total: int | None = None


class SourceInconsistent(Exception):
    """The source contradicts itself (e.g. parts don't add up to its own total)."""


from . import bell, dallas, hays, mclennan, montgomery, travis  # noqa: E402

SCRAPERS = {m.NAME: m for m in (dallas, travis, montgomery, bell, hays, mclennan)}
