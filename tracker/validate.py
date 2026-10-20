"""Validation rules. A reading either passes as reported or is held; nothing is corrected.

Intraday (Tier 2):
  1. cumulative may never drop below the last accepted value
  2. gain may not exceed 3x the fastest accepted pace so far (votes per open poll-hour),
     times the open poll-hours elapsed; floor of 2% of registered voters. Before any pace
     exists (first readings of Day 1), the cap is 15% of registered voters.
  3. cumulative may not exceed registered voters
  4. 0 <= locations reporting <= locations total
  5. same source timestamp as the last accepted reading -> 'unchanged', not a new reading

Daily (Tier 1, SOS): rules 1 and 3, plus a daily gain cap of max(3x the largest prior daily
gain, 2% of registered + 25), or 15% of registered on Day 1. Also held: a figure under 10% of
the same Day N in every past year on file (when that year had 500+ votes). The SOS file shows
partial county submissions, e.g. Harris at 4 votes on Day 1 of 2026 against 126,473 in 2024.
"""
from datetime import datetime, timedelta

UNCHANGED = "unchanged"


def open_hours(start: datetime, end: datetime, hours: dict) -> float:
    """Poll-open hours between two times, using {date: (open_dt, close_dt)}."""
    total = 0.0
    d = start.date()
    while d <= end.date():
        if d in hours:
            o, c = hours[d]
            lo, hi = max(start, o), min(end, c)
            if hi > lo:
                total += (hi - lo).total_seconds() / 3600
        d += timedelta(days=1)
    return total


def check_intraday(r, prev: list[dict], registered: int | None, hours: dict) -> str | None:
    """Return None if valid, UNCHANGED, or a human-readable rejection reason.

    prev: accepted log rows for this county, oldest first (cum_in_person int, source_time datetime).
    """
    if r.cum_in_person < 0:
        return f"negative count {r.cum_in_person}"
    if registered and r.cum_in_person > registered:
        return f"count {r.cum_in_person:,} exceeds registered voters {registered:,}"
    if r.locations_reporting is not None and r.locations_total is not None:
        if not 0 <= r.locations_reporting <= r.locations_total:
            return f"locations reporting {r.locations_reporting} outside 0..{r.locations_total}"
    if not prev:
        if registered and r.cum_in_person > 0.15 * registered:
            return f"first reading {r.cum_in_person:,} exceeds 15% of registered voters"
        return None

    last = prev[-1]
    if r.source_time == last["source_time"]:
        return UNCHANGED
    if r.cum_in_person < last["cum_in_person"]:
        return f"count dropped {last['cum_in_person']:,} -> {r.cum_in_person:,}"

    gain = r.cum_in_person - last["cum_in_person"]
    pace = 0.0
    for a, b in zip(prev, prev[1:]):
        h = open_hours(a["source_time"], b["source_time"], hours)
        if h >= 0.5:
            pace = max(pace, (b["cum_in_person"] - a["cum_in_person"]) / h)
    elapsed = open_hours(last["source_time"], r.source_time, hours)
    if pace == 0:
        cap = 0.15 * registered if registered else None
    else:
        cap = max(3 * pace * max(elapsed, 0.5), 0.02 * (registered or 0))
    if cap is not None and gain > cap:
        return (f"jump of {gain:,} in {elapsed:.1f} open hours exceeds cap {int(cap):,} "
                f"(3x fastest pace {pace:,.0f}/hr)")
    return None


LOW_VS_PAST = 0.10   # a figure under 10% of every past year's same day looks like a partial submission
LOW_MIN_PAST = 500   # ...only applied where those past years had at least this many votes


def check_daily(cum: int, registered: int, day: int, prior: list[int],
                past: dict[int, int] | None = None) -> str | None:
    """prior: accepted cumulative values for Day 1..day-1 (may be shorter if days missing).
    past: {year: cumulative in-person votes at the end of the same Day N} for earlier elections."""
    if cum < 0:
        return f"negative count {cum}"
    big = {y: v for y, v in (past or {}).items() if v and v >= LOW_MIN_PAST}
    if big and all(cum < LOW_VS_PAST * v for v in big.values()):
        then = ", ".join(f"{v:,} in {y}" for y, v in sorted(big.items(), reverse=True))
        return f"only {cum:,} votes, under 10% of the same day before ({then}); county submission looks incomplete"
    if registered and cum > registered:
        return f"count {cum:,} exceeds registered voters {registered:,}"
    if prior and cum < prior[-1]:
        return f"count dropped {prior[-1]:,} -> {cum:,}"
    base = prior[-1] if prior else 0
    gains = [b - a for a, b in zip([0] + prior, prior)]
    if day == 1 or not gains:
        cap = 0.15 * registered
    else:
        cap = max(3 * max(gains), 0.02 * registered + 25)
    if registered and cum - base > cap:
        return f"daily gain {cum - base:,} exceeds cap {int(cap):,}"
    return None
