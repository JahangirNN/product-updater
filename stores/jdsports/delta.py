"""
Store Delta Updater: JD Sports (Nike Footwear Collections)
Polls live price and stock availability for existing JD Sports products.
Enforces pure functional design, zero classes (ADR 0002, ADR 0005, ADR 0008, ADR 0010, ADR 0015, ADR 0016).
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

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Sec-Ch-Ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
}


def check_price_and_stock(
    product: Dict[str, Any],
    client: Optional[httpx.Client] = None,
    store_name: str = "jdsports",
    rate_limiter: Optional[Any] = None,
    browser_page: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Fetch the latest price and stock status for an existing JD Sports product.
    Acquires rate limiter permit, trips circuit breaker on HTTP 429,
    preserves state on HTTP 404 delisting, and extracts granular per-size stock.
    """
    t_start = time.perf_counter()
    resolved_store = store_name or product.get("store") or product.get("source_store") or "jdsports"
    handle = product.get("handle", "")
    sku = product.get("source_sku") or product.get("sku") or ""
    old_source_price = float(product.get("source_price") or 0.0)
    old_availability = product.get("availability", "unknown")
    source_url = product.get("source_url", "")

    if not source_url and sku:
        raw_title = product.get("title", "nike-footwear").lower()
        cleaned_title = re.sub(r"['\u2019]s\b", "s", raw_title)
        slug = re.sub(r'[^a-zA-Z0-9]+', '-', cleaned_title).strip('-')
        source_url = f"https://www.jdsports.com/pdp/{slug}/{sku}"

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

    # 2. Browser solver mode (Camoufox zero-token local Akamai solver)
    if browser_page is not None:
        from stores.jdsports.camoufox_solver import solve_and_extract_pdp
        solve_res = solve_and_extract_pdp(browser_page, source_url, target_handle=handle)
        status = solve_res.get("status")
        elapsed_ms = solve_res.get("elapsed_ms", round((time.perf_counter() - t_start) * 1000, 2))

        if status == "success":
            raw_extracted_variants = solve_res.get("variants", [])
            new_source_price = float(solve_res.get("price_usd") or 0.0)
            if new_source_price <= 0.0:
                new_source_price = old_source_price

            variants_delta = []
            changed_variants = []
            variant_stock_changed = False
            variant_price_changed = False
            changed_variant_prices = []

            stored_variants = {str(v.get("sku", "")).strip(): v for v in product.get("variants", [])}
            stored_by_size = {str(v.get("title", "")).split("/")[0].strip(): v for v in product.get("variants", [])}

            for v in raw_extracted_variants:
                v_sku = str(v.get("sku") or "").strip()
                v_size = str(v.get("size") or "").strip()
                v_price = float(v.get("price_usd") or 0.0)
                v_in_stock = bool(v.get("available", False))

                matched_v = stored_variants.get(v_sku)
                if not matched_v and v_size:
                    for s_k, s_v in stored_by_size.items():
                        if re.search(rf"\b{re.escape(v_size)}\b", s_k):
                            matched_v = s_v
                            break

                if matched_v:
                    old_v_stock = bool(matched_v.get("in_stock", False))
                    old_v_price = float(matched_v.get("source_price") or 0.0)
                    if old_v_stock != v_in_stock:
                        variant_stock_changed = True
                        changed_variants.append({
                            "sku": matched_v.get("sku", v_sku),
                            "old_in_stock": old_v_stock,
                            "new_in_stock": v_in_stock
                        })
                    new_v_p = v_price if v_price > 0 else new_source_price
                    if new_v_p > 0 and old_v_price > 0 and abs(new_v_p - old_v_price) > 0.01:
                        variant_price_changed = True
                        changed_variant_prices.append({
                            "sku": matched_v.get("sku", v_sku),
                            "size": matched_v.get("size") or v_size or "",
                            "old_source_price": old_v_price,
                            "new_source_price": new_v_p
                        })

                variants_delta.append({
                    "sku": v_sku,
                    "size": v_size,
                    "available": v_in_stock,
                    "price_usd": v_price if v_price > 0 else new_source_price
                })

            curr_avail = "in_stock" if any(vd["available"] for vd in variants_delta) else "out_of_stock"
            stock_changed = (curr_avail != old_availability)
            price_changed = abs(new_source_price - old_source_price) > 0.01 if (old_source_price > 0 and new_source_price > 0) else False

            return {
                "status": "success",
                "handle": handle,
                "current_source_price": new_source_price,
                "old_source_price": old_source_price,
                "current_compare_price": product.get("source_compare_at_price"),
                "availability": curr_avail,
                "old_availability": old_availability,
                "is_active": (curr_avail == "in_stock"),
                "price_changed": price_changed,
                "stock_changed": stock_changed,
                "variant_stock_changed": variant_stock_changed,
                "changed_variants": changed_variants,
                "variant_price_changed": variant_price_changed,
                "changed_variant_prices": changed_variant_prices,
                "variants_delta": variants_delta,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "elapsed_ms": elapsed_ms,
                "message": "Polled successfully via Camoufox"
            }

        elif status == "not_found":
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
                "message": "Product delisted (HTTP 404)"
            }

        elif status in ("rate_limited", "blocked"):
            return {
                "status": "rate_limited",
                "handle": handle,
                "availability": old_availability,
                "old_availability": old_availability,
                "current_source_price": old_source_price,
                "old_source_price": old_source_price,
                "is_active": (old_availability == "in_stock"),
                "price_changed": False,
                "stock_changed": False,
                "variant_stock_changed": False,
                "changed_variants": [],
                "variants_delta": [],
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "elapsed_ms": elapsed_ms,
                "message": solve_res.get("error", "Akamai challenge unresolved in browser")
            }

        else:
            return {
                "status": "error",
                "handle": handle,
                "current_source_price": old_source_price,
                "old_source_price": old_source_price,
                "availability": old_availability,
                "old_availability": old_availability,
                "is_active": (old_availability == "in_stock"),
                "price_changed": False,
                "stock_changed": False,
                "variant_stock_changed": False,
                "changed_variants": [],
                "variant_price_changed": False,
                "changed_variant_prices": [],
                "variants_delta": [],
                "error": solve_res.get("error", "Camoufox extraction error"),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "elapsed_ms": elapsed_ms
            }

    # 3. HTTP Fallback Mode
    for attempt in range(3):
        try:
            # 2. Outbound Network Request
            resp = None
            if client:
                resp = client.get(source_url, headers=DEFAULT_HEADERS, follow_redirects=True, timeout=15.0)
            else:
                with httpx.Client() as c:
                    resp = c.get(source_url, headers=DEFAULT_HEADERS, follow_redirects=True, timeout=15.0)

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
                    "variants_delta": [],
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "elapsed_ms": elapsed_ms,
                    "message": "Product delisted (HTTP 404)"
                }

            # 5. HTTP 403 Akamai WAF Shield Handling
            if resp.status_code == 403:
                return {
                    "status": "rate_limited",
                    "handle": handle,
                    "availability": old_availability,
                    "old_availability": old_availability,
                    "current_source_price": old_source_price,
                    "old_source_price": old_source_price,
                    "is_active": (old_availability == "in_stock"),
                    "price_changed": False,
                    "stock_changed": False,
                    "variant_stock_changed": False,
                    "changed_variants": [],
                    "variants_delta": [],
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "elapsed_ms": elapsed_ms,
                    "message": "Akamai Bot Manager 403 Forbidden"
                }

            resp.raise_for_status()

            # 6. Parse JSON-LD from HTML
            html = resp.text
            scripts = re.findall(r'<script[^>]*type=[\'"]application/ld\+json[\'"][^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)

            jsonld_obj = None
            for s_content in scripts:
                try:
                    data = json.loads(s_content.strip())
                    if isinstance(data, list):
                        for item in data:
                            if item.get("@type") in ("ProductGroup", "Product"):
                                jsonld_obj = item
                                break
                    elif isinstance(data, dict):
                        if data.get("@type") in ("ProductGroup", "Product"):
                            jsonld_obj = data
                            break
                    if jsonld_obj:
                        break
                except Exception:
                    continue

            if not jsonld_obj:
                # Delisted or unhydrated stub
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
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "elapsed_ms": elapsed_ms,
                    "message": "JSON-LD schema not found in PDP"
                }

            # Extract variants from ProductGroup
            raw_has_variant = jsonld_obj.get("hasVariant") or []
            if jsonld_obj.get("@type") == "Product":
                raw_has_variant = [jsonld_obj]

            new_source_price = old_source_price
            variants_delta = []
            changed_variants = []
            variant_stock_changed = False
            variant_price_changed = False
            changed_variant_prices = []

            stored_variants = {v.get("sku"): v for v in product.get("variants", [])}
            stored_by_size = {str(v.get("title", "")).split("/")[0].strip(): v for v in product.get("variants", [])}

            for v in raw_has_variant:
                v_sku = str(v.get("sku") or "").strip()
                v_size = str(v.get("size") or "").strip()
                v_offers = v.get("offers") or {}
                if isinstance(v_offers, list) and v_offers:
                    v_offers = v_offers[0]

                v_price = 0.0
                v_in_stock = False
                if isinstance(v_offers, dict):
                    try:
                        v_price = float(v_offers.get("price") or 0.0)
                    except (ValueError, TypeError):
                        v_price = 0.0
                    avail_str = str(v_offers.get("availability") or "").lower()
                    v_in_stock = ("instock" in avail_str or "in_stock" in avail_str)

                if v_price > 0 and (new_source_price == old_source_price or new_source_price == 0.0):
                    new_source_price = v_price

                # Match against stored variant
                matched_v = stored_variants.get(v_sku)
                if not matched_v and v_size:
                    for s_k, s_v in stored_by_size.items():
                        if re.search(rf"\b{re.escape(v_size)}\b", s_k):
                            matched_v = s_v
                            break

                if matched_v:
                    old_v_stock = bool(matched_v.get("in_stock", False))
                    old_v_price = float(matched_v.get("source_price") or 0.0)
                    if old_v_stock != v_in_stock:
                        variant_stock_changed = True
                        changed_variants.append({
                            "sku": matched_v.get("sku", v_sku),
                            "old_in_stock": old_v_stock,
                            "new_in_stock": v_in_stock
                        })
                    new_v_p = v_price if v_price > 0 else new_source_price
                    if new_v_p > 0 and old_v_price > 0 and abs(new_v_p - old_v_price) > 0.01:
                        variant_price_changed = True
                        changed_variant_prices.append({
                            "sku": matched_v.get("sku", v_sku),
                            "size": matched_v.get("size") or v_size or "",
                            "old_source_price": old_v_price,
                            "new_source_price": new_v_p
                        })

                variants_delta.append({
                    "sku": v_sku,
                    "size": v_size,
                    "available": v_in_stock,
                    "price_usd": v_price if v_price > 0 else new_source_price
                })

            curr_avail = "in_stock" if any(v["available"] for v in variants_delta) else "out_of_stock"
            stock_changed = (curr_avail != old_availability)
            price_changed = abs(new_source_price - old_source_price) > 0.01

            return {
                "status": "success",
                "handle": handle,
                "current_source_price": new_source_price,
                "old_source_price": old_source_price,
                "current_compare_price": product.get("source_compare_at_price"),
                "availability": curr_avail,
                "old_availability": old_availability,
                "is_active": (curr_avail == "in_stock"),
                "price_changed": price_changed,
                "stock_changed": stock_changed,
                "variant_stock_changed": variant_stock_changed,
                "changed_variants": changed_variants,
                "variant_price_changed": variant_price_changed,
                "changed_variant_prices": changed_variant_prices,
                "variants_delta": variants_delta,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "elapsed_ms": elapsed_ms,
                "message": "Polled successfully via JSON-LD"
            }

        except Exception as e:
            elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
            if attempt < 2:
                time.sleep(random.uniform(0.5, 1.5))
                continue
            return {
                "status": "error",
                "handle": handle,
                "current_source_price": old_source_price,
                "old_source_price": old_source_price,
                "availability": old_availability,
                "old_availability": old_availability,
                "is_active": (old_availability == "in_stock"),
                "price_changed": False,
                "stock_changed": False,
                "variant_stock_changed": False,
                "changed_variants": [],
                "variant_price_changed": False,
                "changed_variant_prices": [],
                "variants_delta": [],
                "error": str(e),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "elapsed_ms": elapsed_ms
            }

    # If retries exhausted (e.g. on 429)
    elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
    return {
        "status": "rate_limited",
        "handle": handle,
        "availability": old_availability,
        "old_availability": old_availability,
        "current_source_price": old_source_price,
        "old_source_price": old_source_price,
        "is_active": (old_availability == "in_stock"),
        "price_changed": False,
        "stock_changed": False,
        "variant_stock_changed": False,
        "changed_variants": [],
        "variant_price_changed": False,
        "changed_variant_prices": [],
        "variants_delta": [],
        "error": "Rate limit retries exhausted",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_ms": elapsed_ms
    }


def apply_delta_to_product(
    product: Dict[str, Any],
    delta_result: Dict[str, Any],
    forex_rate: float
) -> Tuple[Dict[str, Any], bool]:
    """
    Apply delta check results to a JD Sports canonical product dict.
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

    # 1. Price updates (Whole-Rupee INR Math)
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
                    if re.search(rf"\b{re.escape(s_str)}\b", var.get("title", "")):
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
