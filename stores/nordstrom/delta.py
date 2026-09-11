"""
Store Delta Updater: Nordstrom (On Running Footwear)
Polls price and stock availability for existing products during hourly sync sweeps.
Uses Camoufox stealth browser solver to bypass Kasada without external API costs.
Accurately syncs granular per-size variant inventory (shipQuantity > 0).
Pure functions only, zero classes (ADR 0002, ADR 0005, ADR 0010).
"""
import time
import random
import re
from typing import Any, Dict, List, Optional, Tuple
import httpx

from storage.network import create_http_client, DEFAULT_BROWSER_HEADERS
from storage.rate_limiter import acquire_permit, trip_circuit_breaker, parse_retry_after

DEFAULT_HEADERS = DEFAULT_BROWSER_HEADERS


def norm_size_string(s: str) -> str:
    """Normalize size string: 'US 9.5' -> '9.5', '11.5 M' -> '11.5', '10' -> '10'."""
    m = re.search(r'(\d+(?:\.\d)?)', s)
    return m.group(1) if m else s.strip().lower()


def check_price_and_stock(
    product: Dict[str, Any],
    client: Optional[httpx.Client] = None,
    store_name: str = "nordstrom",
    rate_limiter: Optional[Any] = None,
    browser_page: Optional[Any] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Poll live price and stock status for an existing product.
    Supports local Camoufox stealth browser page to solve Kasada proof-of-work.
    Accurately extracts granular per-size variant availability from window.__INITIAL_CONFIG__.
    Detects Kasada blocks and strictly prevents false-positive 'success' statuses.
    """
    t_start = time.perf_counter()
    resolved_store = store_name or product.get("store") or product.get("source_store") or "nordstrom"
    handle = product.get("handle") or extract_handle_from_url(product.get("source_url", ""))
    url = product.get("source_url") or f"https://www.nordstrom.com/s/{handle}"
    old_source_price = float(product.get("source_price") or 0.0)
    old_availability = product.get("availability", "in_stock")

    # 1. Acquire rate limiter permit
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

    # 2. Browser solver mode (Camoufox with per-size variant tracking)
    if browser_page is not None:
        from stores.nordstrom.camoufox_solver import solve_and_extract_pdp
        solve_res = solve_and_extract_pdp(browser_page, url, target_handle=handle)
        status = solve_res.get("status")
        elapsed_ms = solve_res.get("elapsed_ms", round((time.perf_counter() - t_start) * 1000, 2))

        if status == "success":
            curr_price = float(solve_res.get("price_usd") or 0.0)
            curr_avail = solve_res.get("availability", "in_stock")
            if curr_price == 0.0 and curr_avail == "in_stock":
                curr_price = old_source_price

            size_stock = solve_res.get("size_stock", {})

            # Map granular per-size stock for every variant
            variants_delta = []
            has_any_variant_in_stock = False
            variant_stock_changed = False

            for v in product.get("variants", []):
                v_sku = v.get("sku")
                old_v_in_stock = v.get("in_stock", True)

                # Extract US size and color
                us_sz = ""
                v_col = ""
                for opt in v.get("option_values", []):
                    if "US" in opt.get("option_name", ""):
                        us_sz = opt.get("name", "")
                    if "Color" in opt.get("option_name", ""):
                        v_col = opt.get("name", "").strip().lower()

                if not us_sz:
                    v_title = v.get("title", "")
                    us_sz = v_title.split("/")[0].strip() if "/" in v_title else v_title

                norm_sz = norm_size_string(us_sz)

                if size_stock:
                    var_avail = size_stock.get((norm_sz, v_col))
                    if var_avail is None:
                        var_avail = size_stock.get(norm_sz, False)
                else:
                    var_avail = curr_avail == "in_stock"

                if var_avail:
                    has_any_variant_in_stock = True

                if var_avail != old_v_in_stock:
                    variant_stock_changed = True

                variants_delta.append({
                    "sku": v_sku,
                    "available": var_avail,
                    "price_usd": curr_price
                })

            # If size_stock was available, top-level availability depends on whether ANY variant is in stock
            if size_stock:
                curr_avail = "in_stock" if has_any_variant_in_stock else "out_of_stock"

            price_changed = abs(curr_price - old_source_price) > 0.01 if (old_source_price > 0 and curr_price > 0) else False
            stock_changed = (curr_avail != old_availability) or variant_stock_changed

            return {
                "status": "success",
                "handle": handle,
                "current_source_price": curr_price,
                "old_source_price": old_source_price,
                "current_compare_price": product.get("source_compare_at_price"),
                "availability": curr_avail,
                "old_availability": old_availability,
                "is_active": curr_avail == "in_stock",
                "price_changed": price_changed,
                "stock_changed": stock_changed,
                "size_stock": size_stock,
                "variants_delta": variants_delta,
                "elapsed_ms": elapsed_ms
            }

        elif status == "not_found":
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

        elif status == "blocked":
            return {
                "status": "blocked",
                "handle": handle,
                "availability": old_availability,
                "old_availability": old_availability,
                "current_source_price": old_source_price,
                "old_source_price": old_source_price,
                "is_active": old_availability == "in_stock",
                "price_changed": False,
                "stock_changed": False,
                "elapsed_ms": elapsed_ms,
                "error": "Kasada challenge unresolved in browser"
            }

        else:
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
                "error": solve_res.get("error", "Browser solver extraction error")
            }

    # 3. HTTP Fallback Mode (Strictly checks for Kasada challenge to prevent false success)
    for attempt in range(3):
        try:
            if client:
                resp = client.get(url, timeout=12.0)
            else:
                with create_http_client(timeout_seconds=12.0) as c:
                    resp = c.get(url)

            elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)

            if resp.status_code == 429:
                retry_after_sec = parse_retry_after(resp.headers.get("Retry-After"), default_cooldown=30.0)
                jitter = random.uniform(1.0, 2.0 * (2 ** attempt))
                backoff_duration = retry_after_sec + jitter
                if rate_limiter and callable(getattr(rate_limiter, "trip_circuit_breaker", None)):
                    try:
                        rate_limiter.trip_circuit_breaker(resolved_store, backoff_duration)
                    except TypeError:
                        rate_limiter.trip_circuit_breaker(backoff_duration)
                else:
                    trip_circuit_breaker(resolved_store, backoff_duration)

                if attempt < 2:
                    time.sleep(backoff_duration)
                    continue
                else:
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
            html_text = resp.text

            # CRITICAL: Detect Kasada challenge page and never falsely report success
            if "istlWas" in html_text or not re.search(r'<title>(.+?)</title>', html_text, re.I):
                return {
                    "status": "blocked",
                    "handle": handle,
                    "availability": old_availability,
                    "old_availability": old_availability,
                    "current_source_price": old_source_price,
                    "old_source_price": old_source_price,
                    "is_active": old_availability == "in_stock",
                    "price_changed": False,
                    "stock_changed": False,
                    "elapsed_ms": elapsed_ms,
                    "error": "Kasada bot challenge screen detected on HTTP request (requires Camoufox)"
                }

            is_sold_out = bool(re.search(r'\b(?:sold out|currently unavailable|out of stock)\b', html_text, re.I))
            current_availability = "out_of_stock" if is_sold_out else "in_stock"

            price_match = re.search(r'\$(\d+(?:\.\d{2})?)', html_text)
            if not price_match and not is_sold_out:
                return {
                    "status": "blocked",
                    "handle": handle,
                    "availability": old_availability,
                    "old_availability": old_availability,
                    "current_source_price": old_source_price,
                    "old_source_price": old_source_price,
                    "is_active": old_availability == "in_stock",
                    "price_changed": False,
                    "stock_changed": False,
                    "elapsed_ms": elapsed_ms,
                    "error": "No product pricing found in HTTP response (bot challenge or JS required)"
                }

            current_source_price = float(price_match.group(1)) if price_match else old_source_price
            price_changed = abs(current_source_price - old_source_price) > 0.01 if old_source_price > 0 else False
            stock_changed = current_availability != old_availability

            variants_delta = []
            for v in product.get("variants", []):
                variants_delta.append({
                    "sku": v.get("sku"),
                    "available": current_availability == "in_stock",
                    "price_usd": current_source_price
                })

            return {
                "status": "success",
                "handle": handle,
                "current_source_price": current_source_price,
                "old_source_price": old_source_price,
                "current_compare_price": product.get("source_compare_at_price"),
                "availability": current_availability,
                "old_availability": old_availability,
                "is_active": current_availability == "in_stock",
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
    """Extract product handle from URL."""
    cleaned = url.split("?")[0].rstrip("/")
    parts = [p for p in cleaned.split("/") if p]
    if len(parts) >= 2 and parts[-2] == "s":
        return parts[-1]
    return parts[-1] if parts else "on-shoe"


def apply_delta_to_product(
    product: Dict[str, Any],
    delta_result: Dict[str, Any],
    forex_rate: float
) -> Tuple[Dict[str, Any], bool]:
    """
    Pure function to apply delta check results to a canonical product dictionary.
    Updates price, INR recalculation, overall availability, and granular variant-level stock.
    Sets shopify_sync_pending = True if changes occurred.
    CRITICAL: ONLY stamps last_verified_at when status in ('success', 'not_found').
    Returns (updated_product, has_changed).
    """
    status = delta_result.get("status")
    if status not in ("success", "not_found"):
        # Transient error or blocked or rate-limited: do NOT mutate product data and NEVER stamp last_verified_at
        return product, False

    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    product["last_verified_at"] = now_iso

    price_changed = bool(delta_result.get("price_changed", False))
    stock_changed = bool(delta_result.get("stock_changed", False))
    
    # 1. Update variant states if available and detect variant-level changes
    variant_changes_detected = False
    variants_delta = {v["sku"]: v for v in delta_result.get("variants_delta", []) if v.get("sku")}
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
                if v_info.get("price_usd", 0) > 0:
                    var["price"] = f"{float(round(v_info['price_usd'] * forex_rate)):.2f}"

    has_changed = price_changed or stock_changed or variant_changes_detected

    if not has_changed:
        return product, False

    # Apply price changes
    new_source_price = delta_result.get("current_source_price", product.get("source_price", 0.0))
    product["source_price"] = new_source_price

    # Recalculate INR whole-rupee price
    if new_source_price > 0:
        product["current_price"] = float(round(new_source_price * forex_rate))

    new_compare_price = delta_result.get("current_compare_price")
    if new_compare_price is not None:
        product["compare_at_price"] = float(round(new_compare_price * forex_rate))

    # Apply availability changes
    product["availability"] = delta_result.get("availability", product.get("availability"))
    product["is_active"] = delta_result.get("is_active", product.get("availability") == "in_stock")

    product["shopify_sync_pending"] = True
    product["updated_at"] = now_iso

    return product, True
