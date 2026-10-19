"""McLennan County: ElectionLink live turnout widget (same vendor as Travis).

Not linked from the county site. The widget's title text says "WILLIAMSON COUNTY" - a stale
vendor template (Williamson has no such widget; its slug 404s). The mclennantx slug and the
per-county numbers identify it. Checks are in electionlink.py; the hourly check applies.
"""
from . import electionlink

NAME = "MCLENNAN"
BASE = "https://updates.electionlink.net/widgets/mclennantx/2026-11-03/"


def fetch():
    return electionlink.fetch(BASE, hourly=True)
