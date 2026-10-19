"""Ellis County: ElectionLink live turnout widget (same vendor as Travis).

Not linked from elliscountytx.gov; identified by its ELLIS COUNTY ELECTIONS ADMINISTRATION
header and its site list (Midlothian Conf Center, Palmer ISD Annex, Red Oak Municipal Center).
Checks are in electionlink.py; the hourly check applies.
"""
from . import electionlink

NAME = "ELLIS"
BASE = "https://updates.electionlink.net/widgets/ellistx/2026-11-03/"


def fetch():
    return electionlink.fetch(BASE, hourly=True)
