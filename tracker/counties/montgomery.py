"""Montgomery County: ElectionLink live turnout widget (same vendor as Travis).

The widget is run for Montgomery County Elections Administration (its CSV header says so)
but is not linked from elections.mctx.org. 'Early Vote' is pollbook check-ins, so it is
in-person only; the widget's mail series are empty.

Cross-checks, all from the same refresh:
  - summary 'Early Vote' == Total row of the per-day table == sum of its day rows
  - today's hourly check-ins sum to that day's row in the per-day table
The title line of the CSVs still names a 2021 election (a stale vendor template), so the
date line and lastRefreshed are what identify the data, not the title.
Montgomery does not publish per-site counts, so locations reporting is left blank.
"""
import re
from datetime import datetime, timezone

from .. import net
from ..config import CT
from . import Reading, SourceInconsistent

NAME = "MONTGOMERY"
BASE = "https://updates.electionlink.net/widgets/montgomerytx/2026-11-03/"
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

    # Per-day table: "10/19,13358,0,0,13358," rows, then "Total,13358,0,0,13358,"
    table = net.get_text(BASE + "EarlyVotingTable.csv")
    days = {d: int(n) for d, n in re.findall(r"^(\d{1,2}/\d{1,2}),(\d+),", table, re.M)}
    t = re.search(r"^Total,(\d+),", table, re.M)
    if not days or not t:
        raise SourceInconsistent("per-day early-voting table not found")
    if int(t.group(1)) != early or sum(days.values()) != early:
        raise SourceInconsistent(f"per-day table (rows {sum(days.values())}, total {t.group(1)}) "
                                 f"!= summary {early}")

    # Hourly table covers the current day only.
    hourly = net.get_text(BASE + "CheckinsPerHourTable.csv")
    dm = re.search(r"^(\d{1,2})/(\d{1,2})/2026\s*$", hourly, re.M)
    rows = [int(n) for n in re.findall(r"^\d{1,2}:\d{2} [AP]M - [^,]+,(\d+)\s*$", hourly, re.M)]
    ht = re.search(r"^Total,(\d+)", hourly, re.M)
    if not dm or not rows or not ht:
        raise SourceInconsistent("hourly check-in table not found")
    key = f"{int(dm.group(1))}/{int(dm.group(2))}"
    day_total = next((n for d, n in days.items()
                      if f"{int(d.split('/')[0])}/{int(d.split('/')[1])}" == key), None)
    if sum(rows) != int(ht.group(1)) or day_total is None or sum(rows) != day_total:
        raise SourceInconsistent(f"hourly check-ins for {key} sum {sum(rows)} != that day's total {day_total}")

    if abs((_refreshed(net.get_text(BASE + "CheckinsPerHourGraph.html")) - t_summary).total_seconds()) > 120:
        raise SourceInconsistent("summary and hourly pages refreshed at different times")

    return Reading(cum_in_person=early, source_time=t_summary, source_url=PUBLIC_URL)
