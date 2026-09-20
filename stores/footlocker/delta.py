"""
Store Delta Updater: Foot Locker (Nike Vomero Footwear)
Polls live price and stock availability for existing Foot Locker products.
Enforces pure functional design, zero classes (ADR 0002, ADR 0005, ADR 0010, ADR 0015).
Centralized rate limiting, circuit breaker on 429, 404 delisting preservation,
and selective timestamp stamping.
"""
import time
import random
import json
import re
from typing import Any, Dict, List, Optional, Tuple
import httpx

from storage.network import create_http_client, DEFAULT_BROWSER_HEADERS
from storage.rate_limiter import acquire_permit, trip_circuit_breaker, parse_retry_after
from stores.footlocker.inflow import parse_numeric_size

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}


def check_price_and_stock(
    product: Dict[str, Any],
    client: Optional[httpx.Client] = None,
    store_name: str = "footlocker",
    rate_limiter: Optional[Any] = None,
    browser_page: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Fetch the latest price and stock status for an existing Foot Locker product.
    Acquires rate limiter permit, trips circuit breaker on HTTP 429,
    preserves state on HTTP 404 delisting, and extracts granular per-size stock.
    """
    t_start = time.perf_counter()
    resolved_store = store_name or product.get("store") or product.get("source_store") or "footlocker"
    handle = product.get("handle", "")
    sku = product.get("source_sku") or product.get("sku") or ""
    old_source_price = float(product.get("source_price") or 0.0)
    old_availability = product.get("availability", "unknown")
    source_url = product.get("source_url", "")

    if not source_url and sku:
        raw_title = product.get("title", "nike-vomero").lower()
        cleaned_title = re.sub(r"['\u2019]s\b", "s", raw_title)
        slug = re.sub(r'[^a-zA-Z0-9]+', '-', cleaned_title).strip('-')
        source_url = f"https://www.footlocker.com/product/{slug}/{sku}.html"

    for attempt in range(3):
        try:
            # 1. Thread-safe rate limiter permit acquisition
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

            # 2. Network Request
            resp = None
            if client:
                resp = client.get(source_url, headers=DEFAULT_HEADERS, follow_redirects=True, timeout=20.0)
            else:
                with httpx.Client() as c:
                    resp = c.get(source_url, headers=DEFAULT_HEADERS, follow_redirects=True, timeout=20.0)

            elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)

            # 3. HTTP 429 Handling with Circuit Breaker
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
                    break

            # 4. HTTP 404 Delisting State Preservation (ADR 0008, ADR 0010, ADR 0015)
            if resp.status_code == 404:
                variant_stock_changed = False
                changed_variants = []
                for var in product.get("variants", []):
                    if var.get("in_stock", False):
                        variant_stock_changed = True
                        changed_variants.append({
                            "sku": var.get("sku", ""),
                            "old_in_stock": True,
                            "new_in_stock": False
                        })
                return {
                    "status": "not_found",
                    "handle": handle,
                    "availability": "out_of_stock",
                    "old_availability": old_availability,
                    "new_availability": "out_of_stock",
                    "current_source_price": old_source_price,
                    "old_source_price": old_source_price,
                    "new_source_price": old_source_price,
                    "is_active": False,
                    "price_changed": False,
                    "stock_changed": old_availability != "out_of_stock",
                    "variant_stock_changed": variant_stock_changed,
                    "changed_variants": changed_variants,
                    "variant_price_changed": False,
                    "changed_variant_prices": [],
                    "variants_delta": [],
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "elapsed_ms": elapsed_ms,
                    "message": "Product delisted (HTTP 404)"
                }

            resp.raise_for_status()

            # 5. Extract state from HTML
            html = resp.text
            idx = html.find('STATE_FROM_SERVER:')
            if idx == -1:
                # Delisted or redirected to empty stub
                if "/product/~/" in str(resp.url) or "/~/product/" in str(resp.url) or "not found" in html.lower():
                    variant_stock_changed = False
                    changed_variants = []
                    for var in product.get("variants", []):
                        if var.get("in_stock", False):
                            variant_stock_changed = True
                            changed_variants.append({
                                "sku": var.get("sku", ""),
                                "old_in_stock": True,
                                "new_in_stock": False
                            })
                    return {
                        "status": "not_found",
                        "handle": handle,
                        "availability": "out_of_stock",
                        "old_availability": old_availability,
                        "new_availability": "out_of_stock",
                        "current_source_price": old_source_price,
                        "old_source_price": old_source_price,
                        "new_source_price": old_source_price,
                        "is_active": False,
                        "price_changed": False,
                        "stock_changed": old_availability != "out_of_stock",
                        "variant_stock_changed": variant_stock_changed,
                        "changed_variants": changed_variants,
                        "variants_delta": [],
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "elapsed_ms": elapsed_ms,
                        "message": "Product delisted or unnavigable"
                    }
                raise ValueError("STATE_FROM_SERVER not found in Foot Locker response")

            d, _ = json.JSONDecoder().raw_decode(html[idx + len('STATE_FROM_SERVER:'):].lstrip())
            get_details = d.get('api', {}).get('productDetails', {}).get('getDetails', {})
            data = get_details.get('data', {})
            errors = get_details.get('errors', [])
            status_code = get_details.get('statusCode')

            # Dehydrated state indicates out of stock / delisted (code 20006, 404, or empty data)
            if status_code == 404 or errors or not data or get_details.get("status") == "@api/FAILED":
                variant_stock_changed = False
                changed_variants = []
                for var in product.get("variants", []):
                    if var.get("in_stock", False):
                        variant_stock_changed = True
                        changed_variants.append({
                            "sku": var.get("sku", ""),
                            "old_in_stock": True,
                            "new_in_stock": False
                        })
                err_msg = errors[0].get('message') if errors and isinstance(errors, list) and isinstance(errors[0], dict) else f"HTTP {status_code or 404}"
                return {
                    "status": "not_found",
                    "handle": handle,
                    "availability": "out_of_stock",
                    "old_availability": old_availability,
                    "new_availability": "out_of_stock",
                    "current_source_price": old_source_price,
                    "old_source_price": old_source_price,
                    "new_source_price": old_source_price,
                    "is_active": False,
                    "price_changed": False,
                    "stock_changed": old_availability != "out_of_stock",
                    "variant_stock_changed": variant_stock_changed,
                    "changed_variants": changed_variants,
                    "variants_delta": [],
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "elapsed_ms": elapsed_ms,
                    "message": f"Product out of stock / delisted ({err_msg})"
                }

            style = data.get('style', {})
            raw_sizes = data.get('sizes', [])

            price_obj = style.get('price', {})
            current_source_price = float(price_obj.get('salePrice') or price_obj.get('listPrice') or old_source_price)
            current_compare_price = float(price_obj.get('listPrice')) if price_obj.get('listPrice') else None

            # Build variant delta mapping with parse_numeric_size
            variants_delta = []
            for s_entry in raw_sizes:
                sz_raw = s_entry.get('strippedSize') or s_entry.get('size')
                if sz_raw:
                    numeric_sz = parse_numeric_size(sz_raw)
                    if numeric_sz is None:
                        continue
                    clean_sz = f"{numeric_sz:g}"
                    is_sz_active = bool(s_entry.get('active', False))
                    var_sku = f"{sku}-{clean_sz}"

                    # Extract size-specific price if available, fallback to current_source_price
                    sz_price = current_source_price
                    s_price_obj = s_entry.get('price') if isinstance(s_entry.get('price'), dict) else {}
                    if s_price_obj:
                        p_val = float(s_price_obj.get('salePrice') or s_price_obj.get('listPrice') or 0.0)
                        if p_val > 0:
                            sz_price = p_val
                    elif s_entry.get('salePrice') or s_entry.get('price'):
                        try:
                            p_val = float(s_entry.get('salePrice') or s_entry.get('price') or 0.0)
                            if p_val > 0:
                                sz_price = p_val
                        except (ValueError, TypeError):
                            pass

                    variants_delta.append({
                        "sku": var_sku,
                        "size": clean_sz,
                        "available": is_sz_active,
                        "price_usd": sz_price
                    })

            # Check if any variant is in stock
            if variants_delta:
                has_stock = any(v["available"] for v in variants_delta)
            else:
                has_stock = bool(style.get("active", False))

            current_availability = "in_stock" if has_stock else "out_of_stock"
            is_available = (current_availability == "in_stock")

            price_changed = abs(current_source_price - old_source_price) > 0.01 if old_source_price > 0 else False
            stock_changed = (current_availability != old_availability)

            # Track variant-level stock shifts (ADR 0015) and price shifts (R1)
            variant_stock_changed = False
            changed_variants = []
            variant_price_changed = False
            changed_variant_prices = []
            prod_variants = product.get("variants") or []
            if prod_variants and variants_delta:
                v_delta_map = {v["sku"]: v for v in variants_delta if v.get("sku")}
                size_map = {str(v.get("size")).strip(): v for v in variants_delta if v.get("size")}
                for var in prod_variants:
                    v_sku = var.get("sku")
                    matched_v = v_delta_map.get(v_sku)
                    if not matched_v:
                        for s_str, sv in size_map.items():
                            if v_sku and v_sku.endswith(f"-{s_str}"):
                                matched_v = sv
                                break
                            if re.search(rf"\bUS\s+{re.escape(s_str)}(\.0)?\b", var.get("title", "")):
                                matched_v = sv
                                break
                    if matched_v:
                        old_v_stock = bool(var.get("in_stock", False))
                        new_v_stock = bool(matched_v.get("available", False))
                        if old_v_stock != new_v_stock:
                            variant_stock_changed = True
                            changed_variants.append({
                                "sku": v_sku,
                                "old_in_stock": old_v_stock,
                                "new_in_stock": new_v_stock
                            })
                        old_v_price = float(var.get("source_price") or 0.0)
                        new_v_price = float(matched_v.get("price_usd") or 0.0)
                        if new_v_price > 0 and old_v_price > 0 and abs(new_v_price - old_v_price) > 0.01:
                            variant_price_changed = True
                            changed_variant_prices.append({
                                "sku": v_sku,
                                "size": var.get("size") or var.get("title") or "",
                                "old_source_price": old_v_price,
                                "new_source_price": new_v_price
                            })

            return {
                "status": "success",
                "handle": handle,
                "current_source_price": current_source_price,
                "old_source_price": old_source_price,
                "new_source_price": current_source_price,
                "current_compare_price": current_compare_price,
                "availability": current_availability,
                "old_availability": old_availability,
                "new_availability": current_availability,
                "is_active": is_available,
                "price_changed": price_changed,
                "stock_changed": stock_changed,
                "variant_stock_changed": variant_stock_changed,
                "changed_variants": changed_variants,
                "variant_price_changed": variant_price_changed,
                "changed_variant_prices": changed_variant_prices,
                "variants_delta": variants_delta,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
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


def apply_delta_to_product(
    product: Dict[str, Any],
    delta_result: Dict[str, Any],
    forex_rate: float
) -> Tuple[Dict[str, Any], bool]:
    """
    Apply delta check results to a Foot Locker canonical product dict.
    Updates price, INR recalculation, availability, and variant-level states.
    CRITICAL: ONLY stamp last_verified_at when status in ("success", "not_found").
    Cascades stock depletion on 404 delistings to all child variants (ADR 0015).
    Returns (updated_product, has_changed).
    """
    status = delta_result.get("status")
    if status not in ("success", "not_found"):
        # Transient error or rate limited: do NOT mutate product data and NEVER stamp last_verified_at
        return product, False

    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    product["last_verified_at"] = now_iso

    has_changed = False
    price_changed = bool(delta_result.get("price_changed", False))
    stock_changed = bool(delta_result.get("stock_changed", False))
    variant_stock_changed = bool(delta_result.get("variant_stock_changed", False))
    variant_price_changed = bool(delta_result.get("variant_price_changed", False))

    if price_changed or stock_changed or variant_stock_changed or variant_price_changed:
        has_changed = True

    # 1. Price updates
    new_source_price = float(delta_result.get("current_source_price", product.get("source_price", 0.0)) or 0.0)
    if price_changed and new_source_price > 0:
        product["source_price"] = new_source_price
        product["current_price"] = float(round(new_source_price * forex_rate))
        has_changed = True

    new_compare_price = delta_result.get("current_compare_price")
    if new_compare_price is not None and float(new_compare_price) > 0:
        product["compare_at_price"] = float(round(float(new_compare_price) * forex_rate))

    # 2. Availability & Variants
    variants_delta = delta_result.get("variants_delta", [])
    has_explicit_variant_pricing = any(
        float(v.get("price_usd") or 0.0) > 0 for v in variants_delta if isinstance(v, dict)
    )

    if variants_delta and product.get("variants"):
        v_map = {v["sku"]: v for v in variants_delta if v.get("sku")}
        size_map = {str(v.get("size")).strip(): v for v in variants_delta if v.get("size")}

        for var in product["variants"]:
            v_sku = var.get("sku")
            matched_v = v_map.get(v_sku)
            if not matched_v:
                for s_str, sv in size_map.items():
                    if v_sku and v_sku.endswith(f"-{s_str}"):
                        matched_v = sv
                        break
                    if re.search(rf"\bUS\s+{re.escape(s_str)}(\.0)?\b", var.get("title", "")):
                        matched_v = sv
                        break
            if matched_v:
                new_v_stock = bool(matched_v.get("available", False))
                if var.get("in_stock") != new_v_stock:
                    var["in_stock"] = new_v_stock
                    has_changed = True
                if "is_available" in var and var.get("is_available") != new_v_stock:
                    var["is_available"] = new_v_stock
                    has_changed = True

                new_v_price = float(matched_v.get("price_usd") or 0.0)
                if new_v_price > 0:
                    old_v_price = float(var.get("source_price") or 0.0)
                    if abs(new_v_price - old_v_price) > 0.01:
                        var["source_price"] = new_v_price
                        var["price"] = f"{round(new_v_price * forex_rate):.2f}"
                        var["price_current"] = float(round(new_v_price * forex_rate))
                        has_changed = True
                    else:
                        if "price_current" not in var:
                            var["price_current"] = float(round(new_v_price * forex_rate))
                elif price_changed and new_source_price > 0 and not has_explicit_variant_pricing:
                    old_v_price = float(var.get("source_price") or 0.0)
                    if abs(new_source_price - old_v_price) > 0.01:
                        var["source_price"] = new_source_price
                        var["price"] = f"{round(new_source_price * forex_rate):.2f}"
                        var["price_current"] = float(round(new_source_price * forex_rate))
                        has_changed = True

        # Uniform fallback sync when parent price changed and variants omit individual prices
        if price_changed and new_source_price > 0 and not has_explicit_variant_pricing:
            for var in product.get("variants", []):
                old_v_price = float(var.get("source_price") or 0.0)
                if abs(new_source_price - old_v_price) > 0.01:
                    var["source_price"] = new_source_price
                    var["price"] = f"{round(new_source_price * forex_rate):.2f}"
                    var["price_current"] = float(round(new_source_price * forex_rate))
                    has_changed = True

        # ADR 0015: Derive parent availability strictly from child variant states
        has_any_variant_stock = any(v.get("in_stock", False) for v in product.get("variants", []))
        expected_avail = "in_stock" if has_any_variant_stock else "out_of_stock"
        if product.get("availability") != expected_avail:
            product["availability"] = expected_avail
            has_changed = True
        product["is_active"] = (expected_avail == "in_stock")

    elif not variants_delta and product.get("variants"):
        if price_changed and new_source_price > 0:
            for var in product.get("variants", []):
                old_v_price = float(var.get("source_price") or 0.0)
                if abs(new_source_price - old_v_price) > 0.01:
                    var["source_price"] = new_source_price
                    var["price"] = f"{round(new_source_price * forex_rate):.2f}"
                    var["price_current"] = float(round(new_source_price * forex_rate))
                    has_changed = True

        # ADR 0015 Depletion / Restock Cascade
        target_avail = delta_result.get("availability") or product.get("availability")
        if target_avail in ("out_of_stock", "delisted"):
            # Depletion cascade: all child variants forced out of stock
            if product.get("availability") != target_avail:
                product["availability"] = target_avail
                has_changed = True
            product["is_active"] = False
            for var in product["variants"]:
                if var.get("in_stock") is not False:
                    var["in_stock"] = False
                    has_changed = True
        elif target_avail == "in_stock" and not any(v.get("in_stock", False) for v in product["variants"]):
            # Restock cascade: restore variants
            if product.get("availability") != "in_stock":
                product["availability"] = "in_stock"
                has_changed = True
            product["is_active"] = True
            for var in product["variants"]:
                if var.get("in_stock") is not True:
                    var["in_stock"] = True
                    has_changed = True
    else:
        if stock_changed or delta_result.get("availability"):
            new_avail = delta_result.get("availability", product.get("availability"))
            if product.get("availability") != new_avail:
                product["availability"] = new_avail
                has_changed = True
            product["is_active"] = (product["availability"] == "in_stock")

    if has_changed:
        product["shopify_sync_pending"] = True
        product["updated_at"] = now_iso

    return product, has_changed
