"""Travis County: ElectionLink live turnout widget linked from votetravis.gov.

The summary page's 'Early Vote' count is pollbook check-ins (in-person only). It is
cross-checked against the sum of the hourly check-ins page for every early-voting day.
Travis does not publish per-site counts, so locations reporting is left blank.
"""
import re
from datetime import datetime, timezone

from .. import net
from ..config import CT
from . import Reading, SourceInconsistent

NAME = "TRAVIS"
BASE = "https://updates.electionlink.net/widgets/travistx/2026-11-03/"
PUBLIC_URL = BASE + "index.html"


def _refreshed(page: str) -> datetime:
    m = re.search(r"var lastRefreshed = ([\d.]+);", page)
    if not m:
        raise SourceInconsistent("no lastRefreshed timestamp")
    return datetime.fromtimestamp(float(m.group(1)) / 1000, timezone.utc).astimezone(CT)


def fetch() -> Reading:
    summary = net.get_text(BASE + "BallotTypeTurnout.html")
    m = re.search(r"\['Early Vote',\s*(\d+)\]", summary)
    if not m:
        raise SourceInconsistent("Early Vote count not found on summary page")
    early = int(m.group(1))
    t_summary = _refreshed(summary)

    hourly = net.get_text(BASE + "CheckinsPerHourGraph.html")
    counts = [int(x) for x in re.findall(r"rows\.push\(\['[^']*',\s*(\d+)\]\)", hourly)]
    if not counts:
        raise SourceInconsistent("hourly check-in rows not found")
    if sum(counts) != early:
        raise SourceInconsistent(f"hourly check-ins sum {sum(counts)} != summary {early}")
    if abs((_refreshed(hourly) - t_summary).total_seconds()) > 120:
        raise SourceInconsistent("summary and hourly pages refreshed at different times")

    return Reading(cum_in_person=early, source_time=t_summary, source_url=PUBLIC_URL)
