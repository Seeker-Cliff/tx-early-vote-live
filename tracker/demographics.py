"""Build data/demographics.csv: citizen voting-age population (CVAP) by race/ethnicity per county.

Source: U.S. Census Bureau, CVAP special tabulation from the 2020-2024 ACS 5-year estimates,
  https://www2.census.gov/programs-surveys/decennial/rdo/datasets/2024/2024-cvap/CVAP_2020-2024_ACS_csv_files.zip
Run once per Census release (the file is ~60 MB, so it isn't fetched by the tracker):
  python -m tracker.demographics path/to/CVAP_2020-2024_ACS_csv_files.zip

Groups: Hispanic (any race); White, Black, AAPI (Asian + Native Hawaiian/Pacific Islander)
are non-Hispanic single-race; Other = everything else (AIAN, multiracial).
"""
import csv
import io
import json
import re
import sys
import zipfile

from .config import DATA

OUT = DATA / "demographics.csv"
FIELDS = ["county", "cvap", "white", "hispanic", "black", "aapi", "other"]
LINES = {"Total": "cvap", "White Alone": "white", "Hispanic or Latino": "hispanic",
         "Black or African American Alone": "black", "Asian Alone": "aapi",
         "Native Hawaiian or Other Pacific Islander Alone": "aapi"}


def _key(name: str) -> str:
    return re.sub(r"[^A-Z]", "", name.upper())


def build(zip_path: str) -> None:
    z = zipfile.ZipFile(zip_path)
    text = z.read("County.csv").decode("latin-1")
    rows: dict[str, dict] = {}
    for r in csv.DictReader(io.StringIO(text)):
        if not r["geoid"].startswith("0500000US48"):
            continue
        name = r["geoname"].removesuffix(" County, Texas")
        d = rows.setdefault(name, {k: 0 for k in FIELDS[1:]})
        if r["lntitle"] in LINES:
            d[LINES[r["lntitle"]]] += int(r["cvap_est"])
    names = {_key(n): n for n in json.loads((DATA / "registered.json").read_text())}
    out = []
    for name, d in rows.items():
        k = names.get(_key(name))
        if not k:
            raise SystemExit(f"no SOS county matches Census name {name!r}")
        # Each line is a separate estimate with its own margin of error, so in small counties
        # the groups can sum slightly past the total; Other is then 0, not negative.
        d["other"] = max(0, d["cvap"] - d["white"] - d["hispanic"] - d["black"] - d["aapi"])
        out.append({"county": k, **d})
    if len(out) != 254:
        raise SystemExit(f"expected 254 Texas counties, got {len(out)}")
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(sorted(out, key=lambda r: r["county"]))
    print(f"wrote {OUT} ({len(out)} counties)")


if __name__ == "__main__":
    build(sys.argv[1])
