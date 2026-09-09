"""
Forex Currency Conversion Module
Fetches and caches USD to INR foreign exchange rates.
Pure functions, zero classes (ADR 0005, ADR 0006).
"""
import os
import json
import time
from typing import Dict, Any, Optional
import httpx

FOREX_API_URL = "https://open.er-api.com/v6/latest/USD"
CACHE_TTL_SECONDS = 86400  # 24 hours
DEFAULT_FALLBACK_RATE = 94.0


def fetch_live_rate() -> float:
    """Fetch live USD to INR exchange rate from open API."""
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(FOREX_API_URL)
            resp.raise_for_status()
            data = resp.json()
            rate = float(data.get("rates", {}).get("INR", 0.0))
            if rate > 0:
                return rate
    except Exception as err:
        print(f"[WARN] Failed to fetch live forex rate: {err}")
    return DEFAULT_FALLBACK_RATE


def get_usd_to_inr_rate(cache_path: str = "storage/forex_cache.json") -> float:
    """
    Get USD to INR conversion rate.
    Uses local cache if modified within last 24 hours.
    """
    # 1. Check cache
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
            timestamp = cached_data.get("timestamp", 0)
            rate = cached_data.get("rates", {}).get("INR")
            if rate and (time.time() - timestamp < CACHE_TTL_SECONDS):
                return float(rate)
        except Exception:
            pass

    # 2. Fetch fresh rate
    rate = fetch_live_rate()

    # 3. Write cache atomically
    save_cache(cache_path, rate)
    return rate


def save_cache(cache_path: str, rate: float) -> None:
    """Save exchange rate cache atomically."""
    cache_dir = os.path.dirname(cache_path)
    if cache_dir and not os.path.exists(cache_dir):
        os.makedirs(cache_dir, exist_ok=True)

    cache_data = {
        "timestamp": int(time.time()),
        "base": "USD",
        "rates": {
            "INR": rate
        }
    }
    tmp_path = f"{cache_path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, indent=2)
    os.replace(tmp_path, cache_path)


def convert_usd_to_inr(price_usd: float, rate: float) -> float:
    """Convert USD price to whole INR rupees."""
    if price_usd <= 0:
        return 0.0
    return float(round(price_usd * rate))
