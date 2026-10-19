"""Shared reader for ElectionLink live turnout widgets (updates.electionlink.net/widgets/<slug>/).

'Early Vote' on these widgets is pollbook check-ins, so it is in-person only; provisional /
affidavit and mail are reported separately or not at all. Cross-checks, all one refresh:
  - summary 'Early Vote' == Total row of the per-day table == sum of its day rows
  - (hourly=True) the current day's hourly check-ins sum to that day's row
  - the pages carry the same lastRefreshed time (within 2 minutes)
CSV title lines are stale vendor templates (old election names, sometimes another county's
name), so the date line, the URL slug and lastRefreshed identify the data, never the title.
No per-site counts are published, so locations reporting is left blank.
"""
import re
from datetime import datetime, timezone

from .. import net
from ..config import CT
from . import Reading, SourceInconsistent


def _refreshed(page: str) -> datetime:
    m = re.search(r"var lastRefreshed = ([\d.]+);", page)
    if not m:
        raise SourceInconsistent("no lastRefreshed timestamp")
    return datetime.fromtimestamp(float(m.group(1)) / 1000, timezone.utc).astimezone(CT)


def _md(s: str) -> str:
    m, d = s.split("/")[:2]
    return f"{int(m)}/{int(d)}"


def fetch(base: str, hourly: bool) -> Reading:
    summary = net.get_text(base + "BallotTypeTurnout.html")
    m = re.search(r"\['Early Vote',\s*(\d+)\]", summary)
    if not m:
        raise SourceInconsistent("Early Vote count not found on summary page")
    early = int(m.group(1))
    t_summary = _refreshed(summary)

    # Per-day table: "10/19,13358,0,0,13358," rows, then "Total,13358,...". Early Vote is column 1.
    table = net.get_text(base + "EarlyVotingTable.csv")
    days = {_md(d): int(n) for d, n in re.findall(r"^(\d{1,2}/\d{1,2}),(\d+),", table, re.M)}
    t = re.search(r"^Total,(\d+),", table, re.M)
    if not days or not t:
        raise SourceInconsistent("per-day early-voting table not found")
    if int(t.group(1)) != early or sum(days.values()) != early:
        raise SourceInconsistent(f"per-day table (rows {sum(days.values())}, total {t.group(1)}) "
                                 f"!= summary {early}")

    if hourly:
        # Hourly table covers the current day only.
        h = net.get_text(base + "CheckinsPerHourTable.csv")
        dm = re.search(r"^(\d{1,2}/\d{1,2})/2026\s*$", h, re.M)
        rows = [int(n) for n in re.findall(r"^\d{1,2}:\d{2} [AP]M - [^,]+,(\d+)\s*$", h, re.M)]
        ht = re.search(r"^Total,(\d+)", h, re.M)
        if not dm or not rows or not ht:
            raise SourceInconsistent("hourly check-in table not found")
        day_total = days.get(_md(dm.group(1)))
        if sum(rows) != int(ht.group(1)) or sum(rows) != day_total:
            raise SourceInconsistent(f"hourly check-ins for {dm.group(1)} sum {sum(rows)} "
                                     f"!= that day's total {day_total}")
        if abs((_refreshed(net.get_text(base + "CheckinsPerHourGraph.html")) - t_summary).total_seconds()) > 120:
            raise SourceInconsistent("summary and hourly pages refreshed at different times")

    return Reading(cum_in_person=early, source_time=t_summary, source_url=base + "index.html")
