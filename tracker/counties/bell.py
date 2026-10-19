"""Bell County: ElectionLink live turnout widget (same vendor as Travis).

Not linked from bellcountytx.com; identified by the belltx slug, 10/19/2026 data and
Bell's Early Vote / Provisional split. Checks are in electionlink.py; the hourly check applies.
"""
from . import electionlink

NAME = "BELL"
BASE = "https://updates.electionlink.net/widgets/belltx/2026-11-03/"


def fetch():
    return electionlink.fetch(BASE, hourly=True)
