"""Hockley County: ElectionLink live turnout widget (same vendor as Travis).

Not linked from co.hockley.tx.us; identified by its HOCKLEY COUNTY ELECTIONS ADMINISTRATION
header and 14 precincts. Checks are in electionlink.py; the hourly check applies.
"""
from . import electionlink

NAME = "HOCKLEY"
BASE = "https://updates.electionlink.net/widgets/hockleytx/2026-11-03/"


def fetch():
    return electionlink.fetch(BASE, hourly=True)
