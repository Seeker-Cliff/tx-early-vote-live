"""HTTP helpers (stdlib only, so GitHub Actions needs no installs)."""
import json
import time
import urllib.request

UA = "tx-early-vote-live/1.0 (public turnout tracker; github.com/Seeker-Cliff/tx-early-vote-live)"


def get(url: str, timeout: int = 45, tries: int = 3) -> bytes:
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Cache-Control": "no-cache"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - retried, then re-raised
            last = e
            time.sleep(3 * (i + 1))
    raise last


def get_json(url: str, **kw):
    return json.loads(get(url, **kw).decode("utf-8-sig"))


def get_text(url: str, **kw) -> str:
    return get(url, **kw).decode("utf-8-sig", errors="replace")
