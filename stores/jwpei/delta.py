"""
Store Delta Updater: JW PEI
Fast, lightweight polling for price and stock availability using the storefront AJAX endpoint.
Pure functions only, zero classes (ADR 0002, ADR 0005).
"""
import time
from typing import Any, Dict, Optional
import httpx

TIMEOUT_CONFIG = httpx.Timeout(6.0, connect=3.0)
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


def check_price_and_stock(product: Dict[str, Any], client: Optional[httpx.Client] = None) -> Dict[str, Any]:
    """
    Poll live price and stock status for an existing product.
    
    Uses https://www.jwpei.com/products/{handle}.js (<150ms latency, ~4KB).
    Compares live source_price against stored source_price to prevent false forex alarms.
    """
    t_start = time.perf_counter()
    handle = product.get("handle") or extract_handle_from_url(product.get("source_url", ""))
    old_source_price = float(product.get("source_price") or 0.0)
    old_availability = product.get("availability", "unknown")
    
    url = f"https://www.jwpei.com/products/{handle}.js"

    for attempt in range(3):
        try:
            if client:
                resp = client.get(url)
            else:
                with httpx.Client(headers=DEFAULT_HEADERS, timeout=TIMEOUT_CONFIG) as c:
                    resp = c.get(url)

            elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)

            if resp.status_code == 429:
                time.sleep(1.5 * (attempt + 1))
                continue

            if resp.status_code == 404:
                return {
                    "status": "not_found",
                    "handle": handle,
                    "availability": "out_of_stock",
                    "is_active": False,
                    "price_changed": False,
                    "stock_changed": old_availability != "out_of_stock",
                    "elapsed_ms": elapsed_ms,
                    "message": "Product delisted (HTTP 404)"
                }

            resp.raise_for_status()
            data = resp.json()

            # Parse live price (convert cents to dollars)
            price_cents = data.get("price", 0)
            current_source_price = round(price_cents / 100.0, 2)

            compare_cents = data.get("compare_at_price")
            current_compare_price = round(compare_cents / 100.0, 2) if compare_cents else None

            # Parse live stock
            is_available = bool(data.get("available", False))
            current_availability = "in_stock" if is_available else "out_of_stock"

            # Check deltas
            price_changed = abs(current_source_price - old_source_price) > 0.01 if old_source_price > 0 else False
            stock_changed = current_availability != old_availability

            # Variant level info
            raw_variants = data.get("variants", [])
            variants_delta = []
            for v in raw_variants:
                v_cents = v.get("price", 0)
                variants_delta.append({
                    "sku": v.get("sku"),
                    "available": v.get("available", False),
                    "price_usd": round(v_cents / 100.0, 2)
                })

            return {
                "status": "success",
                "handle": handle,
                "current_source_price": current_source_price,
                "old_source_price": old_source_price,
                "current_compare_price": current_compare_price,
                "availability": current_availability,
                "old_availability": old_availability,
                "is_active": is_available,
                "price_changed": price_changed,
                "stock_changed": stock_changed,
                "variants_delta": variants_delta,
                "elapsed_ms": elapsed_ms
            }

        except Exception as err:
            if attempt == 2:
                elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
                return {
                    "status": "error",
                    "handle": handle,
                    "availability": old_availability,
                    "is_active": old_availability == "in_stock",
                    "price_changed": False,
                    "stock_changed": False,
                    "elapsed_ms": elapsed_ms,
                    "error": str(err)
                }
            time.sleep(1.0)

    elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
    return {
        "status": "rate_limited",
        "handle": handle,
        "availability": old_availability,
        "is_active": old_availability == "in_stock",
        "price_changed": False,
        "stock_changed": False,
        "elapsed_ms": elapsed_ms,
        "error": "Rate limit retries exhausted (HTTP 429)"
    }


def extract_handle_from_url(url: str) -> str:
    """Extract product handle from full URL."""
    cleaned = url.split("?")[0].rstrip("/")
    return cleaned.split("/")[-1]
