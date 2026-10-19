# Texas early vote, live

In-person early-vote turnout for the November 3, 2026 Texas general election, compared with the same point in 2024, 2022 and 2018.

**Dashboard:** https://seeker-cliff.github.io/tx-early-vote-live/

## What it tracks

| Tier | Counties | How often | Source |
|---|---|---|---|
| 1 | All 254 | Once a day (the morning after) | Texas Secretary of State early-voting turnout feed |
| 2 | Dallas, Travis | Intraday, starting 2.5 h after polls open, then every 2 h until 30 min after close | Each county's own live feed |

Comparisons are made by **Day N of early voting** (Day 1 = Oct 19, 2026 / Oct 21, 2024 / Oct 24, 2022 / Oct 22, 2018). The 2018 SOS data covers only the 30 largest counties.

## Nothing unverified is shown

Every reading is validated before it is logged. A reading that fails is written to `data/quarantine.csv`, shown on the dashboard only as a **HELD** marker, and reported as a GitHub issue. Nothing is estimated or corrected automatically. The rules are in [`tracker/validate.py`](tracker/validate.py).

## Files

- `data/log.csv`: accepted intraday readings
- `data/daily_2026.csv`: accepted SOS daily figures
- `data/quarantine.csv`: held readings, with the reason each was held
- `data/attempts.csv`: every scheduled intraday attempt (ok / held / unchanged / no_data)
- `data/hours.csv`: poll hours per county, with the source for each
- `data/history/`: 2024, 2022 and 2018 SOS daily history
