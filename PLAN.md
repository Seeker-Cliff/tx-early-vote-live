# Texas Early-Vote Live Tracker — Plan

## Goal
Track 2026 early in-person turnout for all 254 Texas counties, compared with the same point in 2024, 2022 and 2018, on a public dashboard that never shows a number that failed validation.

## Context
Built for Cliff Walker (Seeker Strategies) for the November 2026 general. Early voting runs Oct 19–30, 2026. Cliff isn't a programmer, so Claude handles all code, git and GitHub. The repo `Seeker-Cliff/tx-early-vote-live` is public; the dashboard is served on GitHub Pages and contains numbers and sources only, with no client names or commentary.

## Process Overview
1. Tier 1: each morning, pull the SOS daily cumulative in-person count for all 254 counties.
2. Load SOS daily history for 2024, 2022 (all counties) and 2018 (top 30 counties).
3. Tier 2: one intraday scraper per county that publishes intraday numbers, each run on that county's own schedule, starting with Dallas and Travis.
4. Validate every reading. Failures go to quarantine and never reach the log or the dashboard.
5. Rebuild the dashboard after every run.

## Detailed Steps

### Step 1: Tier 1, daily SOS pull
**What happens:** Download the SOS cumulative early-vote count for every county for the previous day: in-person, mail, and registered voters.
**Input:** SOS early voting turnout feed (goelect.txelections.civixapps.com).
**Output:** Rows in `data/daily.csv`.
**Notes:** The SOS posts the day's numbers the following morning. We count in-person votes only.

### Step 2: History
**What happens:** For past elections, store each county's cumulative in-person count by Day N.
**Day 1 dates:** 2026 = Oct 19, 2024 = Oct 21, 2022 = Oct 24, 2018 = Oct 22.
**Sources:** earlyvoting.texas-election.com for 2022 and 2024 (all counties); SOS 2018 daily pages, which cover the 30 largest counties only.
**Intraday history:** the Wayback Machine snapshot of the county's page nearest the same hour, within ±1 hour. If there is none, fall back to the SOS end-of-day number, labeled "EOD." Nothing is estimated. A snapshot that doesn't line up with the SOS daily total is discarded.

### Step 3: Tier 2, intraday counties
**What happens:** One scraper per county, each tested live before it goes into the schedule.
**Schedule:** first run 2.5 hours after the county's polls open, then every 2 hours, last run 30 minutes after polls close. Each county's hours come from its official notice and are stored in `data/hours.csv` with a link to the source. GitHub Actions starts a check every 30 minutes, and only counties whose run is due get scraped.
**Output:** `data/log.csv`: county, scrape timestamp (Central), cumulative in-person votes, locations reporting, source URL.
**Order:** Dallas, then Travis, then the other intraday counties, largest first.

### Step 4: Validation and quarantine
A reading is rejected if:
1. Its cumulative count is lower than the last accepted value.
2. Its gain is more than 3× the largest gain between two runs so far today (on Day 1, the cap is 15% of registered voters).
3. Its cumulative count is above registered voters.
4. Locations reporting is below 0 or above the county's number of vote centers.
5. It shows the same source timestamp as the previous reading. This marks it as not new rather than rejecting it.
6. Its last intraday reading differs from the next-day SOS total by more than 5%. This flags that day's series rather than rejecting a single reading.

A rejected reading goes to `data/quarantine.csv` with the reason, and a GitHub issue is opened. Nothing is corrected automatically.

### Step 5: Dashboard
- Pick any county, or the statewide total.
- Each county card shows the current count, % ahead or behind each past year, the update time, and the source of each comparison number.
- Tier 2 counties get an intraday chart; Tier 1 counties get a daily chart.
- **HELD:** amber border and badge, the last valid value in gray, a dashed line after the last good point, and hollow amber markers with a tooltip giving the rejected value and reason.
- **NO DATA:** red badge and a gap in the line.
- **SOS disagreement:** a striped band on that day.
- A filter to show only counties with held data.

## Edge Cases and Failure Modes
- A county site is down or its page layout changed: the reading is logged as NO DATA and the other counties still run.
- GitHub's scheduler runs 5–20 minutes late: we always record the actual scrape time.
- 2018 has no data for counties outside the top 30: the dashboard shows "n/a — SOS 2018 covers top 30 only."

## Dependencies and Requirements
- GitHub account Seeker-Cliff (signed in on this machine), a public repo, and Pages enabled.
- Python 3.12 running in GitHub Actions.

## Success Criteria
- All 254 counties are selectable with daily comparisons, starting Oct 20.
- Dallas and Travis intraday readings are logged on schedule, with zero unvalidated numbers shown.
