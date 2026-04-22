"""Exchange rate fetcher (free public API, no key)."""
import logging
import os
import time
from typing import Dict

import requests

log = logging.getLogger("helix.fx")

EXCHANGE_RATE_API = os.environ.get("EXCHANGE_RATE_API", "https://open.er-api.com/v6/latest/USD")

_cache: Dict[str, object] = {"rates": None, "fetched_at": 0, "source": None}
_TTL = 60 * 30  # 30 min


def get_rates() -> dict:
    now = time.time()
    if _cache["rates"] and (now - _cache["fetched_at"]) < _TTL:
        return {"rates": _cache["rates"], "fetched_at": _cache["fetched_at"], "source": _cache["source"]}
    try:
        r = requests.get(EXCHANGE_RATE_API, timeout=8)
        r.raise_for_status()
        data = r.json()
        rates = data.get("rates", {})
        _cache["rates"] = rates
        _cache["fetched_at"] = now
        _cache["source"] = "open.er-api.com"
        return {"rates": rates, "fetched_at": now, "source": "open.er-api.com"}
    except Exception as e:
        log.warning("fx fetch failed: %s", e)
        # fallback static
        fallback = {"NGN": 1650.0, "USD": 1.0, "GBP": 0.79, "EUR": 0.92}
        return {"rates": fallback, "fetched_at": now, "source": "fallback-static"}


def usd_to_ngn(usd: float) -> float:
    r = get_rates()["rates"].get("NGN", 1650.0)
    return round(usd * r, 2)


def ngn_to_usd(ngn: float) -> float:
    r = get_rates()["rates"].get("NGN", 1650.0)
    return round(ngn / r, 2) if r else 0.0
