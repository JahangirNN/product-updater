"""
Store Delta Updater Template: [Store Name]
Production-grade blueprint for onboarding any new retailer delta poller.
Pure functional composition, zero classes (ADR 0002, ADR 0005, ADR 0010).
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
    store_name: str = "template_store",
    rate_limiter: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Fetch the latest price and stock status for an existing product.

    Implement retailer-specific extraction inside the retry loop:
    - Prefer fast internal JSON / AJAX endpoints (e.g. Shopify .js, Magento API, WooCommerce REST).
    - Otherwise, perform lightweight targeted HTML/DOM fetch.
    - Preserves old_availability and price fields on 404 delisting.
    - Acquires thread-safe rate limiter permit and trips circuit breaker on HTTP 429.
    """
    t_start = time.perf_counter()
    resolved_store = store_name or product.get("store") or product.get("source_store") or "template_store"
    handle = product.get("handle") or extract_handle_from_url(product.get("source_url", ""))
    old_source_price = float(product.get("source_price") or 0.0)
    old_availability = product.get("availability", "unknown")
    source_url = product.get("source_url", "")

    for attempt in range(3):
        try:
            # 1. Acquire rate limiter permit before dispatching network request
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

            # 2. Execute lightweight HTTP fetch (replace with store-specific URL/logic)
            if client:
                resp = client.get(source_url)
            else:
                with create_http_client() as c:
                    resp = c.get(source_url)

            elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)

            # 3. Handle 429 Rate Limiting with exponential jitter backoff & circuit breaking
            if resp.status_code == 429:
                retry_after_sec = parse_retry_after(resp.headers.get("Retry-After"))
                jitter = random.uniform(1.0, 2.0 * (2 ** attempt))
                backoff_duration = retry_after_sec + jitter

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

            # 4. Handle 404 Delisting preserving existing product prices
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
                    "variant_stock_changed": False,
                    "changed_variants": [],
                    "variant_price_changed": False,
                    "changed_variant_prices": [],
                    "variants_delta": [],
                    "elapsed_ms": elapsed_ms,
                    "message": "Product delisted (HTTP 404)"
                }

            resp.raise_for_status()

            # 5. Extract price and availability from response (customize per retailer)
            # Default placeholder extraction:
            current_source_price = old_source_price
            current_availability = old_availability
            is_available = current_availability == "in_stock"

            price_changed = abs(current_source_price - old_source_price) > 0.01 if old_source_price > 0 else False
            stock_changed = current_availability != old_availability

            variants_delta = []
            variant_stock_changed = False
            changed_variants = []
            variant_price_changed = False
            changed_variant_prices = []

            for v in product.get("variants", []):
                v_sku = v.get("sku")
                old_v_in_stock = v.get("in_stock", True)
                old_v_price = float(v.get("source_price") or 0.0)
                new_v_avail = (current_availability == "in_stock")
                new_v_price = float(v.get("source_price") or current_source_price)

                if new_v_avail != old_v_in_stock:
                    variant_stock_changed = True
                    changed_variants.append({
                        "sku": v_sku,
                        "old_in_stock": old_v_in_stock,
                        "new_in_stock": new_v_avail
                    })

                if new_v_price > 0 and old_v_price > 0 and abs(new_v_price - old_v_price) > 0.01:
                    variant_price_changed = True
                    changed_variant_prices.append({
                        "sku": v_sku,
                        "size": v.get("title", ""),
                        "old_source_price": old_v_price,
                        "new_source_price": new_v_price
                    })

                variants_delta.append({
                    "sku": v_sku,
                    "available": new_v_avail,
                    "price_usd": new_v_price
                })

            return {
                "status": "success",
                "handle": handle,
                "current_source_price": current_source_price,
                "old_source_price": old_source_price,
                "current_compare_price": None,
                "availability": current_availability,
                "old_availability": old_availability,
                "is_active": is_available,
                "price_changed": price_changed,
                "stock_changed": stock_changed,
                "variant_stock_changed": variant_stock_changed,
                "changed_variants": changed_variants,
                "variant_price_changed": variant_price_changed,
                "changed_variant_prices": changed_variant_prices,
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
                    "variant_stock_changed": False,
                    "changed_variants": [],
                    "variant_price_changed": False,
                    "changed_variant_prices": [],
                    "variants_delta": [],
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
        "variant_stock_changed": False,
        "changed_variants": [],
        "variant_price_changed": False,
        "changed_variant_prices": [],
        "variants_delta": [],
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
    ONLY stamps last_verified_at if status in ('success', 'not_found').
    Returns (updated_product, has_changed).
    """
    status = delta_result.get("status")
    if status not in ("success", "not_found"):
        # Transient error or rate limited: do NOT mutate product data and NEVER stamp last_verified_at
        return product, False

    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    product["last_verified_at"] = now_iso

    price_changed = bool(delta_result.get("price_changed", False))
    stock_changed = bool(delta_result.get("stock_changed", False))
    variant_price_changed = bool(delta_result.get("variant_price_changed", False))
    variant_stock_changed = bool(delta_result.get("variant_stock_changed", False))

    # 1. Update variant states if available and detect variant-level changes
    variant_changes_detected = False
    raw_variants_delta = delta_result.get("variants_delta", [])
    variants_delta = {v["sku"]: v for v in raw_variants_delta if v.get("sku")}

    if variants_delta and product.get("variants"):
        for var in product["variants"]:
            sku = var.get("sku")
            if sku in variants_delta:
                v_info = variants_delta[sku]
                old_v_stock = var.get("in_stock", True)
                new_v_stock = v_info.get("available", False)
                if old_v_stock != new_v_stock:
                    variant_changes_detected = True
                var["in_stock"] = new_v_stock

                # Granular per-variant pricing update: tri-fields
                new_v_price = float(v_info.get("price_usd") or 0.0)
                if new_v_price > 0:
                    old_v_price = float(var.get("source_price") or 0.0)
                    if abs(new_v_price - old_v_price) > 0.01:
                        var["source_price"] = new_v_price
                        var["price"] = f"{round(new_v_price * forex_rate):.2f}"
                        var["price_current"] = float(round(new_v_price * forex_rate))
                        variant_changes_detected = True

                new_v_comp = float(v_info.get("compare_price_usd") or 0.0)
                if new_v_comp > 0:
                    old_v_comp = float(var.get("source_compare_at_price") or 0.0)
                    if abs(new_v_comp - old_v_comp) > 0.01:
                        var["source_compare_at_price"] = new_v_comp
                        var["compare_at_price"] = f"{round(new_v_comp * forex_rate):.2f}"
                        variant_changes_detected = True

    elif not variants_delta and product.get("variants"):
        # ADR 0015: Depletion / Restock Cascade when variants_delta is empty
        target_avail = delta_result.get("availability") or product.get("availability")
        if target_avail in ("out_of_stock", "delisted"):
            for var in product["variants"]:
                if var.get("in_stock") is not False:
                    var["in_stock"] = False
                    variant_changes_detected = True
        elif target_avail == "in_stock" and not any(v.get("in_stock", False) for v in product["variants"]):
            for var in product["variants"]:
                if var.get("in_stock") is not True:
                    var["in_stock"] = True
                    variant_changes_detected = True

    # Uniform pricing fallback: if parent price changed, synchronize variants if they have uniform pricing
    curr_source_price = float(delta_result.get("current_source_price") or 0.0)
    has_explicit_variant_pricing = any(float(v.get("price_usd") or 0.0) > 0 for v in raw_variants_delta) if raw_variants_delta else False
    if price_changed and curr_source_price > 0 and not has_explicit_variant_pricing:
        for var in product.get("variants", []):
            old_vp = float(var.get("source_price") or 0.0)
            if abs(curr_source_price - old_vp) > 0.01:
                var["source_price"] = curr_source_price
                var["price"] = f"{round(curr_source_price * forex_rate):.2f}"
                var["price_current"] = float(round(curr_source_price * forex_rate))
                variant_changes_detected = True

    has_changed = price_changed or stock_changed or variant_price_changed or variant_stock_changed or variant_changes_detected

    if not has_changed:
        return product, False

    # Apply parent price changes
    new_source_price = delta_result.get("current_source_price", product.get("source_price", 0.0))
    product["source_price"] = new_source_price

    # Recalculate INR whole-rupee price
    if new_source_price > 0:
        product["current_price"] = float(round(new_source_price * forex_rate))
        product["price"] = f"{round(new_source_price * forex_rate):.2f}"

    new_compare_price = delta_result.get("current_compare_price")
    if new_compare_price is not None:
        product["compare_at_price"] = float(round(new_compare_price * forex_rate))

    # Apply availability changes
    product["availability"] = delta_result.get("availability", product.get("availability"))
    product["is_active"] = delta_result.get("is_active", product.get("availability") == "in_stock")

    product["shopify_sync_pending"] = True
    product["updated_at"] = now_iso

    return product, True
