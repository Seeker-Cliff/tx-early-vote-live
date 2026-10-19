"""Montgomery County: ElectionLink live turnout widget (same vendor as Travis).

Run for Montgomery County Elections Administration (its CSV header says so) but not linked
from elections.mctx.org. Checks are in electionlink.py; the hourly check applies.
"""
from . import electionlink

NAME = "MONTGOMERY"
BASE = "https://updates.electionlink.net/widgets/montgomerytx/2026-11-03/"


def fetch():
    return electionlink.fetch(BASE, hourly=True)
