"""Build data/history/daily_history.csv from SOS daily cumulative counts.

2024 and 2022 come from earlyvoting.texas-election.com (Cloudflare-protected, so they were
pulled once through a browser into raw_2024.txt / raw_2022.txt and verified by checksum).
2018 comes from the old SOS static pages, which only cover the 30 largest counties.

Flags (a flagged value is never used as a comparison):
  decrease  - cumulative count went down vs the prior day
  missing   - zero while a later day is non-zero
  stalled   - identical to the prior value for 3+ consecutive days (county stopped reporting)
  series_unreliable - another day in the same county-year is flagged
"""
import html
import re

from . import net
from .config import DAY1, EV_DAYS, HIST, date_for_day
from .store import write_all

FIELDS = ["year", "day_n", "date", "county", "registered_voters", "cum_in_person", "flag", "source"]
SRC_NEW = "https://earlyvoting.texas-election.com/Elections/getElectionDetails.do"
SRC_2018 = "https://www.sos.state.tx.us/elections/earlyvoting/2018/{}.shtml"


def _raw(year: int) -> dict[str, tuple[int, list[int]]]:
    out = {}
    for line in (HIST / f"raw_{year}.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        county, reg, vals = line.split("|")
        out[county.upper()] = (int(reg), [int(v) for v in vals.split()])
    return out


def _cell(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def fetch_2018() -> dict[str, tuple[int, list[int]]]:
    out: dict[str, tuple[int, list]] = {}
    for n in range(1, EV_DAYS + 1):
        d = date_for_day(n, 2018)
        slug = d.strftime("%b").lower() + str(d.day)  # oct22 ... nov2
        page = net.get(SRC_2018.format(slug)).decode("latin1")
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S | re.I)
        cells = [[_cell(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S | re.I)] for r in rows]
        hdr = cells[0]
        if "Cumulative In-Person" not in hdr[3]:
            raise ValueError(f"2018 {slug}: unexpected header {hdr}")
        for c in cells[1:]:
            if len(c) < 4:
                continue
            name = c[0].upper()
            reg, cum = int(c[1].replace(",", "")), int(c[3].replace(",", ""))
            out.setdefault(name, (reg, [None] * EV_DAYS))[1][n - 1] = cum
    return out


def flags(vals: list) -> list[str]:
    f = [""] * len(vals)
    for i, v in enumerate(vals):
        if v is None:
            f[i] = "missing"
            continue
        if v == 0 and any((x or 0) > 0 for x in vals[i + 1:]):
            f[i] = "missing"
        if i and vals[i - 1] is not None and v < vals[i - 1]:
            f[i] = "decrease"
    run = 0
    for i in range(1, len(vals)):
        run = run + 1 if vals[i] is not None and vals[i] == vals[i - 1] else 0
        if run >= 3:
            for j in range(i - run + 1, i + 1):
                f[j] = f[j] or "stalled"
    return f


def build() -> int:
    rows = []
    sources = {2024: _raw(2024), 2022: _raw(2022), 2018: fetch_2018()}
    for year, data in sources.items():
        for county, (reg, vals) in data.items():
            if county == "TOTAL":
                # 2018 pages only cover the 30 largest counties, so their total is not statewide.
                county = "STATEWIDE" if year != 2018 else "TOP30_TOTAL"
            fl = flags(vals)
            if any(fl):
                # One broken day makes the whole county-year suspect; never compare against it.
                fl = [f or "series_unreliable" for f in fl]
            for n, v in enumerate(vals, start=1):
                rows.append({
                    "year": year, "day_n": n, "date": date_for_day(n, year).isoformat(),
                    "county": county, "registered_voters": reg,
                    "cum_in_person": "" if v is None else v, "flag": fl[n - 1],
                    "source": SRC_NEW if year != 2018 else SRC_2018.format(
                        date_for_day(n, 2018).strftime("%b").lower() + str(date_for_day(n, 2018).day)),
                })
    write_all(HIST / "daily_history.csv", FIELDS, rows)
    return len(rows)


if __name__ == "__main__":
    print(build(), "rows")
    assert DAY1
