"""Dallas County: ArcGIS feature layer behind the county's Vote Center Finder.

Each early-voting center (L_Poll_Typ = 'EV') carries C_Daily_Tot (today) and C_Tot_Vts
(cumulative for the election). In-person only; mail ballots are not in this layer.
"""
from datetime import datetime, timezone
from urllib.parse import urlencode

from .. import net
from ..config import CT
from . import Reading, SourceInconsistent

NAME = "DALLAS"
LAYER = ("https://services3.arcgis.com/zqe2kwz79KUqUvxC/arcgis/rest/services/"
         "Vote_Center_Finder_view/FeatureServer/4")
PUBLIC_URL = "https://experience.arcgis.com/experience/8204fc2e36cd4fac8729efcedd4fda7f/page/Page?views=Early-Voting"


def fetch() -> Reading:
    meta = net.get_json(LAYER + "?f=json")
    edited = meta["editingInfo"]["dataLastEditDate"]
    q = urlencode({"where": "L_Poll_Typ='EV'", "outFields": "L_Poll_VC,L_Crnt_Sta,C_Daily_Tot,C_Tot_Vts",
                   "returnGeometry": "false", "f": "json", "resultRecordCount": 2000})
    d = net.get_json(f"{LAYER}/query?{q}")
    if "error" in d:
        raise RuntimeError(f"ArcGIS error: {d['error']}")
    if d.get("exceededTransferLimit"):
        raise SourceInconsistent("ArcGIS returned a truncated result")
    sites = [f["attributes"] for f in d["features"]]
    if not sites:
        raise SourceInconsistent("no early-voting sites in layer")
    for s in sites:
        daily, tot = s["C_Daily_Tot"] or 0, s["C_Tot_Vts"] or 0
        if daily < 0 or tot < 0 or daily > tot:
            raise SourceInconsistent(f"site {s['L_Poll_VC']}: daily {daily} > cumulative {tot}")
    return Reading(
        cum_in_person=sum(s["C_Tot_Vts"] or 0 for s in sites),
        source_time=datetime.fromtimestamp(edited / 1000, timezone.utc).astimezone(CT),
        source_url=PUBLIC_URL,
        locations_reporting=sum(1 for s in sites if (s["C_Daily_Tot"] or 0) > 0),
        locations_total=sum(1 for s in sites if s["L_Crnt_Sta"] == "Active"),
    )
