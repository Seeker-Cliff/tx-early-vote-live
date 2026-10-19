"""Build docs/data.json, the only thing the dashboard reads.

Only accepted values become data points. Held readings appear solely as markers carrying
their rejected value and reason; NO DATA attempts appear as gaps.
"""
import json
from datetime import datetime

from . import store
from .config import COMPARE_YEARS, DOCS, HIST, day_n, iso, now_ct
from .counties import SCRAPERS
from .run import load_hours

SOS_MISMATCH = 0.05  # intraday final vs next-day SOS figure


def _int(s):
    return int(s) if s not in ("", None) else None


def build() -> None:
    now = now_ct()
    hist: dict[str, dict[int, list]] = {}
    for r in store.read(HIST / "daily_history.csv"):
        y, n = int(r["year"]), int(r["day_n"])
        hist.setdefault(r["county"], {}).setdefault(y, [None] * 12)[n - 1] = {
            "cum": _int(r["cum_in_person"]), "flag": r["flag"], "reg": _int(r["registered_voters"])}

    intraday_hist: dict[str, list] = {}
    p = HIST / "intraday_history.csv"
    for r in store.read(p):
        intraday_hist.setdefault(r["county"], []).append({
            "year": int(r["year"]), "day_n": int(r["day_n"]), "time": r["time"],
            "cum": int(r["cum_in_person"]), "source": r["source"]})

    reg = json.loads((store.DATA / "registered.json").read_text()) if (store.DATA / "registered.json").exists() else {}
    daily: dict[str, list] = {}
    for r in store.read(store.DAILY):
        daily.setdefault(r["county"], [None] * 12)[int(r["day_n"]) - 1] = int(r["cum_in_person"])

    log, quar, attempts = store.read(store.LOG), store.read(store.QUARANTINE), store.read(store.ATTEMPTS)
    hours = load_hours()

    names = sorted(set(reg) | set(daily) | {c for c in hist if c not in ("STATEWIDE", "TOP30_TOTAL")})
    counties = []
    for name in names:
        c = {
            "name": name, "tier": 2 if name in SCRAPERS else 1,
            "registered": reg.get(name),
            "daily": daily.get(name, [None] * 12),
            "history": {str(y): hist.get(name, {}).get(y) for y in COMPARE_YEARS},
            "daily_held": [{"day_n": int(q["day_n"]), "value": _int(q["cum_in_person"]), "reason": q["reason"],
                            "at": q["scraped_at"]} for q in quar if q["tier"] == "daily" and q["county"] == name],
        }
        if name in SCRAPERS:
            ok = [r for r in log if r["county"] == name]
            c["intraday"] = {
                "readings": [{"t": r["source_time"], "scraped": r["scraped_at"], "cum": int(r["cum_in_person"]),
                              "lr": _int(r["locations_reporting"]), "lt": _int(r["locations_total"]),
                              "url": r["source_url"]} for r in ok],
                "held": [{"t": q["source_time"], "scraped": q["scraped_at"], "value": _int(q["cum_in_person"]),
                          "reason": q["reason"]} for q in quar if q["tier"] == "intraday" and q["county"] == name],
                "no_data": [{"t": a["scraped_at"], "detail": a["detail"]} for a in attempts
                            if a["county"] == name and a["status"] == "no_data"],
                "last_attempt": next(({"t": a["scraped_at"], "status": a["status"], "detail": a["detail"]}
                                      for a in reversed(attempts) if a["county"] == name), None),
                "hours": {d.isoformat(): [o.strftime("%H:%M"), cl.strftime("%H:%M")]
                          for d, (o, cl) in hours.get(name, {}).items()},
                "history": intraday_hist.get(name, []),
            }
            # Rule 6: last intraday reading of each day vs the SOS end-of-day figure.
            checks = []
            for n in range(1, 13):
                day_reads = [r for r in ok if _int(r["day_n"]) == n]
                sos = c["daily"][n - 1]
                if day_reads and sos:
                    last = int(day_reads[-1]["cum_in_person"])
                    diff = (last - sos) / sos
                    checks.append({"day_n": n, "intraday": last, "sos": sos, "diff": round(diff, 4),
                                   "flag": abs(diff) > SOS_MISMATCH})
            c["sos_check"] = checks
        counties.append(c)

    # Statewide: per Day N, compare only counties that have a valid number in both years,
    # so a county missing in one year never inflates or deflates the comparison.
    statewide = []
    for n in range(1, 13):
        have = [c for c in counties if c["daily"][n - 1] is not None]
        if not have:
            statewide.append(None)
            continue
        row = {"day_n": n, "cum": sum(c["daily"][n - 1] for c in have), "counties": len(have), "compare": {}}
        for y in COMPARE_YEARS:
            pairs = [(c["daily"][n - 1], c["history"][str(y)][n - 1]) for c in have
                     if c["history"][str(y)] and c["history"][str(y)][n - 1]
                     and c["history"][str(y)][n - 1]["cum"] is not None and not c["history"][str(y)][n - 1]["flag"]]
            if pairs:
                row["compare"][str(y)] = {"now": sum(a for a, _ in pairs), "then": sum(b for _, b in pairs),
                                          "counties": len(pairs)}
        statewide.append(row)

    out = {
        "generated_at": iso(now),
        "day_n": day_n(now.date()),
        "compare_years": COMPARE_YEARS,
        "statewide": statewide,
        "statewide_history": {str(y): hist.get("STATEWIDE" if y != 2018 else "TOP30_TOTAL", {}).get(y)
                              for y in COMPARE_YEARS},
        "counties": counties,
    }
    DOCS.mkdir(exist_ok=True)
    (DOCS / "data.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print(f"build: docs/data.json ({len(counties)} counties)")
    assert isinstance(now, datetime)
