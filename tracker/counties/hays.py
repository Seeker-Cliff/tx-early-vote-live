"""Hays County: ElectionLink live turnout widget, linked from the county's Nov 3, 2026 election
page ("Polling Place Wait Times"). Early Vote excludes affidavit ballots, which are a
separate column. Hays leaves its hourly table empty, so only the per-day table check applies.
"""
from . import electionlink

NAME = "HAYS"
BASE = "https://updates.electionlink.net/widgets/haystx/2026-11-03/"


def fetch():
    return electionlink.fetch(BASE, hourly=False)
