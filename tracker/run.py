"""Entry point.

  python -m tracker.run daily                 SOS Tier 1 pull for all 254 counties
  python -m tracker.run intraday              Tier 2 counties whose scheduled slot is due
  python -m tracker.run intraday --force X    run county X now regardless of schedule (live test)
  python -m tracker.run build                 rebuild docs/data.json for the dashboard
  python -m tracker.run all                   daily + intraday + build (what GitHub Actions runs)

Any newly held reading is written to holds.md so the workflow can open a GitHub issue.
"""
import base64
import json
import sys
import traceback
from datetime import date, datetime, timedelta

from . import net, store
from .config import CT, DATA, ROOT, SOS_ELECTION_ID, day_n, iso, now_ct
from .counties import SCRAPERS
from .validate import UNCHANGED, check_daily, check_intraday

SOS_API = "https://goelect.txelections.civixapps.com/api-ivis-system/api/v1/getFile"
SOS_PUBLIC = "https://goelect.txelections.civixapps.com/ivis-evr-ui/evr"
REGISTERED = DATA / "registered.json"
HOLDS = ROOT / "holds.md"


def _hold(lines: list[str], text: str) -> None:
    lines.append(f"- {text}")


# ---------------------------------------------------------------- hours & slots
def load_hours() -> dict[str, dict[date, tuple[datetime, datetime]]]:
    out: dict = {}
    for r in store.read(store.HOURS):
        d = date.fromisoformat(r["date"])
        o = datetime.combine(d, datetime.strptime(r["open"], "%H:%M").time(), CT)
        c = datetime.combine(d, datetime.strptime(r["close"], "%H:%M").time(), CT)
        out.setdefault(r["county"], {})[d] = (o, c)
    return out


def slots(open_: datetime, close: datetime) -> list[datetime]:
    """First run 2.5h after open, then every 2h, last run 0.5h after close."""
    end = close + timedelta(minutes=30)
    s, t = [], open_ + timedelta(hours=2, minutes=30)
    while t < end:
        s.append(t)
        t += timedelta(hours=2)
    s.append(end)
    return s


# ---------------------------------------------------------------- Tier 1: SOS daily
def _sos_day(d: date) -> dict:
    url = f"{SOS_API}?type=EVR_EARLYVOTING&electionId={SOS_ELECTION_ID}&electionDate={d:%m/%d/%Y}"
    raw = net.get_json(url)
    payload = json.loads(base64.b64decode(raw["upload"]).decode("utf-8"))
    if len(payload.get("turnout_by_county", [])) != 254:
        raise ValueError(f"SOS {d}: expected 254 counties, got {len(payload.get('turnout_by_county', []))}")
    return payload


def run_daily(holds: list[str]) -> None:
    now = now_ct()
    today = now.date()
    fetched: dict[int, dict] = {}
    for n in range(1, 13):
        d = date(2026, 10, 18) + timedelta(days=n)
        # The SOS file for a date fills in while that day is still voting, so a date only
        # counts as an end-of-day number from 9 AM the next morning. Earlier dates are
        # re-pulled every run, so late county submissions and SOS revisions flow in.
        if now < datetime.combine(d + timedelta(days=1), datetime.min.time(), CT) + timedelta(hours=9):
            if not fetched:
                fetched_reg = _sos_day(d)  # still need registered voters for the intraday caps
                REGISTERED.write_text(json.dumps(
                    {c["name"]: c["registered_voters"] for c in fetched_reg["turnout_by_county"]},
                    indent=0, sort_keys=True))
            break
        fetched[n] = _sos_day(d)

    reg = {c["name"]: c["registered_voters"] for c in fetched[max(fetched)]["turnout_by_county"]} if fetched else {}
    if reg:
        REGISTERED.write_text(json.dumps(reg, indent=0, sort_keys=True))

    old = {(r["day_n"], r["county"]): r for r in store.read(store.DAILY)}
    seen_q = {(q["county"], q["day_n"], q["cum_in_person"]) for q in store.read(store.QUARANTINE) if q["tier"] == "daily"}
    rows = []
    by_county: dict[str, list] = {}
    for n, p in sorted(fetched.items()):
        for c in p["turnout_by_county"]:
            by_county.setdefault(c["name"], []).append((n, c))
    for county, days in by_county.items():
        accepted: list[int] = []
        for n, c in days:
            cum = c["total_in_person_votes_for_election"]
            if cum == 0:
                continue  # not reported yet (SOS posts zeros until the county submits)
            reason = check_daily(cum, c["registered_voters"], n, accepted)
            if reason:
                if (county, str(n), str(cum)) not in seen_q:
                    store.append(store.QUARANTINE, store.QUAR_FIELDS, {
                        "tier": "daily", "county": county, "scraped_at": iso(now), "day_n": n,
                        "cum_in_person": cum, "reason": reason, "source_url": SOS_PUBLIC})
                    _hold(holds, f"**{county}** SOS Day {n}: {cum:,} held — {reason}")
                continue
            accepted.append(cum)
            prev = old.get((str(n), county))
            same = prev and prev["cum_in_person"] == str(cum)
            rows.append({
                "date": p_date(n), "day_n": n, "county": county,
                "registered_voters": c["registered_voters"], "cum_in_person": cum,
                "cum_mail": c["total_mail_votes_for_election"],
                "fetched_at": prev["fetched_at"] if same else iso(now), "flag": ""})
    store.write_all(store.DAILY, store.DAILY_FIELDS, rows)
    print(f"daily: {len(rows)} accepted county-days across {len(fetched)} SOS dates")


def p_date(n: int) -> str:
    return (date(2026, 10, 18) + timedelta(days=n)).isoformat()


# ---------------------------------------------------------------- Tier 2: intraday
def _accepted(county: str) -> list[dict]:
    rows = [r for r in store.read(store.LOG) if r["county"] == county]
    for r in rows:
        r["cum_in_person"] = int(r["cum_in_person"])
        r["source_time"] = datetime.fromisoformat(r["source_time"])
    return rows


def run_intraday(holds: list[str], force: str | None = None) -> None:
    now = now_ct()
    hours = load_hours()
    reg = json.loads(REGISTERED.read_text()) if REGISTERED.exists() else {}
    done = {(a["county"], a["slot"]) for a in store.read(store.ATTEMPTS)}

    for name, mod in SCRAPERS.items():
        if force and name != force.upper():
            continue
        h = hours.get(name, {}).get(now.date())
        if force:
            slot = "manual-" + iso(now)
        else:
            if not h:
                continue
            due = [s for s in slots(*h) if s <= now]
            if not due or (name, iso(due[-1])) in done:
                continue
            slot = iso(due[-1])

        base = {"county": name, "slot": slot, "scraped_at": iso(now)}
        try:
            r = mod.fetch()
        except Exception as e:  # noqa: BLE001 - any failure is a NO DATA attempt, never a number
            detail = f"{type(e).__name__}: {e}"
            store.append(store.ATTEMPTS, store.ATTEMPT_FIELDS, {**base, "status": "no_data", "detail": detail[:300]})
            print(f"{name}: NO DATA — {detail}")
            if type(e).__name__ == "SourceInconsistent":
                _hold(holds, f"**{name}** source inconsistent at {iso(now)} — {e}")
            continue

        r.source_time = r.source_time.replace(microsecond=0)  # log stores whole seconds
        reason = check_intraday(r, _accepted(name), reg.get(name), hours.get(name, {}))
        row = {"county": name, "scraped_at": iso(now), "source_time": iso(r.source_time),
               "day_n": day_n(r.source_time.date()) or "", "cum_in_person": r.cum_in_person,
               "locations_reporting": "" if r.locations_reporting is None else r.locations_reporting,
               "locations_total": "" if r.locations_total is None else r.locations_total,
               "source_url": r.source_url}
        if reason == UNCHANGED:
            store.append(store.ATTEMPTS, store.ATTEMPT_FIELDS, {**base, "status": "unchanged",
                         "detail": f"source still at {iso(r.source_time)}"})
            print(f"{name}: unchanged since {iso(r.source_time)}")
        elif reason:
            store.append(store.QUARANTINE, store.QUAR_FIELDS, {**row, "tier": "intraday", "reason": reason})
            store.append(store.ATTEMPTS, store.ATTEMPT_FIELDS, {**base, "status": "held", "detail": reason})
            _hold(holds, f"**{name}** reading {r.cum_in_person:,} at {iso(r.source_time)} held — {reason}")
            print(f"{name}: HELD — {reason}")
        else:
            store.append(store.LOG, store.LOG_FIELDS, row)
            store.append(store.ATTEMPTS, store.ATTEMPT_FIELDS, {**base, "status": "ok", "detail": ""})
            print(f"{name}: ok {r.cum_in_person:,} in person, locations "
                  f"{row['locations_reporting'] or '-'}/{row['locations_total'] or '-'}, source time {iso(r.source_time)}")


# ---------------------------------------------------------------- main
def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "all"
    force = argv[argv.index("--force") + 1] if "--force" in argv else None
    holds: list[str] = []
    failed = False
    steps = {"daily": ["daily"], "intraday": ["intraday"], "build": ["build"],
             "all": ["daily", "intraday", "build"]}[cmd]
    for step in steps:
        try:
            if step == "daily":
                run_daily(holds)
            elif step == "intraday":
                run_intraday(holds, force)
            elif step == "build":
                from .dashboard import build
                build()
        except Exception:  # noqa: BLE001 - keep later steps running; the workflow still fails visibly
            traceback.print_exc()
            failed = True
    if holds:
        HOLDS.write_text("Readings held by validation (not shown on the dashboard):\n\n" + "\n".join(holds) + "\n")
        print("\n".join(holds))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
