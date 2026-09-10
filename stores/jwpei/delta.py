"""
Store Delta Updater: JW PEI
Fast, lightweight polling for price and stock availability using the storefront AJAX endpoint.
Pure functions only, zero classes (ADR 0002, ADR 0005, ADR 0010).
"""
import time
import random
from typing import Any, Dict, List, Optional, Tuple
import httpx

from storage.network import create_http_client, DEFAULT_BROWSER_HEADERS
from storage.rate_limiter import acquire_permit, trip_circuit_breaker, parse_retry_after

DEFAULT_HEADERS = DEFAULT_BROWSER_HEADERS


def check_price_and_stock(
    product: Dict[str, Any],
    client: Optional[httpx.Client] = None,
    store_name: str = "jwpei",
    rate_limiter: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Poll live price and stock status for an existing product.

    Uses https://www.jwpei.com/products/{handle}.js (<150ms latency, ~4KB).
    Compares live source_price against stored source_price to prevent false forex alarms.
    Applies per-store rate limiting permit and trips circuit breaker on 429.
    Preserves old_availability and price fields on 404 delisting.
    """
    t_start = time.perf_counter()
    resolved_store = store_name or product.get("store") or product.get("source_store") or "jwpei"
    handle = product.get("handle") or extract_handle_from_url(product.get("source_url", ""))
    old_source_price = float(product.get("source_price") or 0.0)
    old_availability = product.get("availability", "unknown")

    url = f"https://www.jwpei.com/products/{handle}.js"

    for attempt in range(3):
        try:
            # 1. Acquire rate limiter permit before making request
            if rate_limiter and callable(getattr(rate_limiter, "acquire_permit", None)):
                try:
                    rate_limiter.acquire_permit(resolved_store)
                except TypeError:
                    rate_limiter.acquire_permit()
            elif isinstance(rate_limiter, dict):
                acquire_fn = rate_limiter.get("acquire_permit")
                if callable(acquire_fn):
                    try:
                        acquire_fn(resolved_store)
                    except TypeError:
                        acquire_fn()
                else:
                    acquire_permit(
                        resolved_store,
                        requests_per_second=rate_limiter.get("requests_per_second"),
                        delay_seconds=rate_limiter.get("delay_seconds")
                    )
            else:
                acquire_permit(resolved_store)

            # 2. Issue request
            if client:
                resp = client.get(url)
            else:
                with create_http_client() as c:
                    resp = c.get(url)

            elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)

            if resp.status_code == 429:
                retry_after_sec = parse_retry_after(resp.headers.get("Retry-After"))
                jitter = random.uniform(1.0, 2.0 * (2 ** attempt))
                backoff_duration = retry_after_sec + jitter

                # Trip store circuit breaker so sibling threads pause immediately
                if rate_limiter and callable(getattr(rate_limiter, "trip_circuit_breaker", None)):
                    try:
                        rate_limiter.trip_circuit_breaker(resolved_store, backoff_duration)
                    except TypeError:
                        rate_limiter.trip_circuit_breaker(backoff_duration)
                elif isinstance(rate_limiter, dict) and callable(rate_limiter.get("trip_circuit_breaker")):
                    try:
                        rate_limiter["trip_circuit_breaker"](resolved_store, backoff_duration)
                    except TypeError:
                        rate_limiter["trip_circuit_breaker"](backoff_duration)
                else:
                    trip_circuit_breaker(resolved_store, backoff_duration)

                if attempt < 2:
                    time.sleep(backoff_duration)
                    continue
                else:
                    # Final attempt exhausted: breaker tripped, exit immediately without redundant sleep
                    break

            if resp.status_code == 404:
                return {
                    "status": "not_found",
                    "handle": handle,
                    "availability": "out_of_stock",
                    "old_availability": old_availability,
                    "current_source_price": old_source_price,
                    "old_source_price": old_source_price,
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
                    "old_availability": old_availability,
                    "current_source_price": old_source_price,
                    "old_source_price": old_source_price,
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
        "old_availability": old_availability,
        "current_source_price": old_source_price,
        "old_source_price": old_source_price,
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


def apply_delta_to_product(
    product: Dict[str, Any],
    delta_result: Dict[str, Any],
    forex_rate: float
) -> Tuple[Dict[str, Any], bool]:
    """
    Pure function to apply delta check results to a canonical product dict.
    Updates price, INR recalculation, availability, and variant-level states.
    Sets shopify_sync_pending = True if changes occurred.
    ONLY stamps last_verified_at if status in ('success', 'not_found').
    Returns (updated_product, has_changed).
    """
    status = delta_result.get("status")
    if status not in ("success", "not_found"):
        # Transient error or rate limited, don't mutate product data and NEVER stamp last_verified_at
        return product, False

    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    product["last_verified_at"] = now_iso

    price_changed = bool(delta_result.get("price_changed", False))
    stock_changed = bool(delta_result.get("stock_changed", False))
    has_changed = price_changed or stock_changed

    if not has_changed:
        return product, False

    # Apply price changes
    new_source_price = delta_result.get("current_source_price", product.get("source_price", 0.0))
    product["source_price"] = new_source_price

    # Recalculate INR price
    if new_source_price > 0:
        product["current_price"] = float(round(new_source_price * forex_rate))

    new_compare_price = delta_result.get("current_compare_price")
    if new_compare_price is not None:
        product["compare_at_price"] = float(round(new_compare_price * forex_rate))

    # Apply availability changes
    product["availability"] = delta_result.get("availability", product.get("availability"))
    product["is_active"] = delta_result.get("is_active", product.get("availability") == "in_stock")

    # Update variant states if available
    variants_delta = {v["sku"]: v for v in delta_result.get("variants_delta", []) if v.get("sku")}
    if variants_delta and product.get("variants"):
        for var in product["variants"]:
            sku = var.get("sku")
            if sku in variants_delta:
                v_info = variants_delta[sku]
                var["is_available"] = v_info.get("available", False)
                if v_info.get("price_usd", 0) > 0:
                    var["price_current"] = float(round(v_info["price_usd"] * forex_rate))

    product["shopify_sync_pending"] = True
    product["updated_at"] = now_iso

    return product, True
