"""
Store Delta Updater: Michael Kors (Handbags, Wallets, Shoes, Sunglasses, Belts)
Polls price, overall stock, and variant-level size stock availability during hourly sync sweeps.
Uses Michael Kors' native SFCC Demandware AJAX API for sub-second, geo-independent polling,
with Camoufox stealth browser as seamless fallback.
Pure functions only, zero classes (ADR 0002, ADR 0005, ADR 0008, ADR 0010).
"""
import time
import random
import re
import json
from typing import Any, Dict, List, Optional, Tuple
import httpx

try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

from storage.network import create_http_client, DEFAULT_BROWSER_HEADERS
from storage.rate_limiter import acquire_permit, trip_circuit_breaker, parse_retry_after

DEFAULT_HEADERS = DEFAULT_BROWSER_HEADERS


def extract_handle_from_url(url: str) -> str:
    """Extract product handle from Michael Kors URL."""
    m = re.search(r'michaelkors\.com/([^/]+)/[A-Z0-9\-]+\.html', url)
    return m.group(1) if m else "product"


def is_variant_in_stock(variant: Dict[str, Any], selectable_sizes: List[str], all_size_values: List[str]) -> bool:
    """
    Determine if a variant is in stock based on selectable sizes from SFCC Demandware.
    If no size variations exist on the product, variant stock is determined by overall availability.
    """
    if not all_size_values:
        return True
    if not selectable_sizes:
        return False

    v_sku = str(variant.get("sku", "")).strip().lower()
    v_title = str(variant.get("title", "")).strip().lower()
    size_opt = ""
    for opt in variant.get("option_values", []):
        if opt.get("option_name", "").lower() in ("size", "waist", "length"):
            size_opt = str(opt.get("name", "")).strip().lower()
            break

    for s_size in selectable_sizes:
        s_clean = str(s_size).strip().lower()
        if not s_clean:
            continue
        # 1. Match word boundary in size_opt (e.g. 'US 6 / UK 4' -> '6')
        if re.search(r'(?:\b|_)' + re.escape(s_clean) + r'(?:\b|_)', size_opt):
            return True
        # 2. Match SKU suffix: -6 or -6.5 or -s
        if v_sku.endswith("-" + s_clean) or v_sku.endswith("_" + s_clean):
            return True
        # 3. Match in title (e.g. 'S (32")' -> '32' or 's')
        if re.search(r'(?:\b|_)' + re.escape(s_clean) + r'(?:\b|_)', v_title):
            return True

    return False


def fetch_sfcc_product_data(
    sku: str,
    color: str = "",
    timeout: float = 10.0,
    browser_page: Optional[Any] = None
) -> Tuple[Optional[Dict[str, Any]], int, str]:
    """
    Query Michael Kors SFCC Demandware AJAX variation endpoint.
    Forces en_US and Sites-mk_us-Site to eliminate geo-redirects and get clean JSON.
    Returns (product_dict, http_status_code, error_message).
    """
    endpoint = f"https://www.michaelkors.com/on/demandware.store/Sites-mk_us-Site/en_US/Product-Variation?pid={sku}&format=ajax"
    if color:
        endpoint += f"&dwvar_{sku}_color={color}"

    # 1. Try curl_cffi with chrome120 impersonation (fastest, ~350ms, zero Akamai block)
    if HAS_CURL_CFFI:
        try:
            resp = cffi_requests.get(endpoint, impersonate="chrome120", timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("product"), 200, ""
            elif resp.status_code in (404, 500):
                # SFCC returns 500 or 404 when product is delisted
                return None, resp.status_code, "Product not found or delisted"
            elif resp.status_code == 429:
                return None, 429, "Rate limited"
        except Exception as exc:
            pass

    # 2. Fallback to Camoufox browser page if available
    if browser_page is not None:
        try:
            browser_page.goto(endpoint, wait_until="domcontentloaded", timeout=int(timeout * 1000))
            text = browser_page.evaluate("() => document.body.innerText")
            data = json.loads(text)
            if "product" in data:
                return data.get("product"), 200, ""
        except Exception as exc:
            pass

    # 3. Standard HTTP client fallback
    try:
        with httpx.Client(timeout=timeout, headers=DEFAULT_HEADERS) as client:
            resp = client.get(endpoint)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("product"), 200, ""
            return None, resp.status_code, f"HTTP {resp.status_code}"
    except Exception as exc:
        return None, 0, str(exc)


def check_price_and_stock(
    product: Dict[str, Any],
    client: Optional[httpx.Client] = None,
    store_name: str = "michaelkors",
    rate_limiter: Optional[Any] = None,
    browser_page: Optional[Any] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Poll live price, overall stock, and variant-level size stock status for a Michael Kors product.
    Queries native SFCC Demandware AJAX endpoint, maps variant stock matrices,
    and preserves state on 404 delisting.
    """
    t_start = time.perf_counter()
    resolved_store = store_name or product.get("source_store") or "michaelkors"
    handle = product.get("handle") or extract_handle_from_url(product.get("source_url", ""))
    url = product.get("source_url") or f"https://www.michaelkors.com/{handle}"
    sku = product.get("source_sku", "")
    old_source_price = float(product.get("source_price") or 0.0)
    old_availability = product.get("availability", "in_stock")
    stored_variants = product.get("variants", [])

    # Extract base SKU if not directly provided
    if not sku:
        m = re.search(r'/([A-Z0-9\-]+)\.html', url)
        if m:
            sku = m.group(1)
        elif stored_variants:
            sku = stored_variants[0].get("sku", "").split("-")[0]

    # Extract color code from source_url if present
    color = ""
    m_col = re.search(r'dwvar_[A-Z0-9\-]+_color=([0-9A-Za-z]+)', url)
    if m_col:
        color = m_col.group(1)

    # 1. Acquire rate limiter permit
    if rate_limiter and callable(getattr(rate_limiter, "acquire_permit", None)):
        try:
            rate_limiter.acquire_permit(resolved_store)
        except TypeError:
            rate_limiter.acquire_permit()
    else:
        acquire_permit(resolved_store)

    # 2. Query SFCC Demandware variation data
    p_data, status_code, err_msg = fetch_sfcc_product_data(
        sku=sku,
        color=color,
        timeout=12.0,
        browser_page=browser_page
    )

    elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)

    # 3. Handle rate limits and errors
    if status_code == 429:
        trip_circuit_breaker(resolved_store, 30)
        return {
            "status": "rate_limited",
            "handle": handle,
            "availability": old_availability,
            "old_availability": old_availability,
            "current_source_price": old_source_price,
            "old_source_price": old_source_price,
            "price_changed": False,
            "stock_changed": False,
            "variant_stock_changed": False,
            "changed_variants": [],
            "variant_price_changed": False,
            "changed_variant_prices": [],
            "variants_delta": [],
            "elapsed_ms": elapsed_ms,
            "message": "HTTP 429 rate limit encountered"
        }

    if status_code == 404:
        changed_variants = [
            {"sku": v.get("sku"), "old_in_stock": v.get("in_stock", True), "new_in_stock": False}
            for v in stored_variants if v.get("in_stock", True)
        ]
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
            "variant_stock_changed": bool(changed_variants),
            "changed_variants": changed_variants,
            "variant_price_changed": False,
            "changed_variant_prices": [],
            "variants_delta": [{"sku": v.get("sku"), "size": v.get("size") or v.get("title") or "", "available": False, "in_stock": False, "price_usd": old_source_price, "source_price": old_source_price} for v in stored_variants],
            "elapsed_ms": elapsed_ms,
            "message": "Product delisted (HTTP 404)"
        }

    if not p_data:
        return {
            "status": "error",
            "handle": handle,
            "availability": old_availability,
            "old_availability": old_availability,
            "current_source_price": old_source_price,
            "old_source_price": old_source_price,
            "price_changed": False,
            "stock_changed": False,
            "variant_stock_changed": False,
            "changed_variants": [],
            "variant_price_changed": False,
            "changed_variant_prices": [],
            "variants_delta": [],
            "elapsed_ms": elapsed_ms,
            "message": f"SFCC query failed: {err_msg} (status {status_code})"
        }

    # 4. Extract price
    price_obj = p_data.get("price") or {}
    curr_price = old_source_price
    sales_obj = price_obj.get("sales") if isinstance(price_obj, dict) else None
    list_obj = price_obj.get("list") if isinstance(price_obj, dict) else None

    if isinstance(sales_obj, dict) and sales_obj.get("value") is not None and float(sales_obj["value"]) > 0:
        curr_price = float(sales_obj["value"])
    elif isinstance(list_obj, dict) and list_obj.get("value") is not None and float(list_obj["value"]) > 0:
        curr_price = float(list_obj["value"])

    compare_price = None
    if isinstance(list_obj, dict) and list_obj.get("value") is not None and float(list_obj["value"]) > 0:
        compare_price = float(list_obj["value"])

    # 5. Extract overall availability
    is_avail = bool(p_data.get("available", False))
    is_ready = bool(p_data.get("readyToOrder", False))
    curr_avail = "in_stock" if (is_avail and is_ready) else ("in_stock" if is_avail else "out_of_stock")

    # 6. Extract size stock matrix from variationAttributes
    selectable_sizes = []
    all_sizes = []
    for va in p_data.get("variationAttributes", []):
        if va.get("displayName") in ("Size", "Waist", "Length"):
            for v in va.get("values", []):
                d_val = str(v.get("displayValue") or v.get("id") or "").strip()
                all_sizes.append(d_val)
                if v.get("selectable"):
                    selectable_sizes.append(d_val)

    # 7. Map variant-level stock and price shifts (R1)
    variants_delta = []
    variant_stock_changed = False
    changed_variants = []
    variant_price_changed = False
    changed_variant_prices = []

    for var in stored_variants:
        v_sku = var.get("sku", "")
        old_v_stock = var.get("in_stock", True)
        old_v_price = float(var.get("source_price") or 0.0)

        if curr_avail == "out_of_stock":
            new_v_stock = False
        elif not all_sizes:
            new_v_stock = True
        else:
            new_v_stock = is_variant_in_stock(var, selectable_sizes, all_sizes)

        if new_v_stock != old_v_stock:
            variant_stock_changed = True
            changed_variants.append({
                "sku": v_sku,
                "old_in_stock": old_v_stock,
                "new_in_stock": new_v_stock
            })

        new_v_price = curr_price
        if new_v_price > 0 and old_v_price > 0 and abs(new_v_price - old_v_price) > 0.01:
            variant_price_changed = True
            changed_variant_prices.append({
                "sku": v_sku,
                "size": var.get("size") or var.get("title") or "",
                "old_source_price": old_v_price,
                "new_source_price": new_v_price
            })

        variants_delta.append({
            "sku": v_sku,
            "size": var.get("size") or var.get("title") or "",
            "available": new_v_stock,
            "in_stock": new_v_stock,
            "price_usd": new_v_price,
            "source_price": new_v_price
        })

    # If all variants are out of stock, overall product is out of stock
    if variants_delta and not any(vd.get("available", vd.get("in_stock", False)) for vd in variants_delta):
        curr_avail = "out_of_stock"

    price_changed = (curr_price != old_source_price)
    stock_changed = (curr_avail != old_availability)

    return {
        "status": "success",
        "handle": handle,
        "availability": curr_avail,
        "old_availability": old_availability,
        "current_source_price": curr_price,
        "old_source_price": old_source_price,
        "new_source_price": curr_price,
        "current_compare_price": compare_price,
        "price_changed": price_changed,
        "stock_changed": stock_changed,
        "variant_stock_changed": variant_stock_changed,
        "changed_variants": changed_variants,
        "variant_price_changed": variant_price_changed,
        "changed_variant_prices": changed_variant_prices,
        "selectable_sizes": selectable_sizes,
        "all_sizes": all_sizes,
        "variants_delta": variants_delta,
        "elapsed_ms": elapsed_ms,
        "message": f"Polled SFCC AJAX: ${curr_price}, {curr_avail}, {len(selectable_sizes)}/{len(all_sizes)} sizes in stock"
    }


def apply_delta_to_product(
    product: Dict[str, Any],
    delta_result: Dict[str, Any],
    forex_rate: float
) -> Tuple[Dict[str, Any], bool]:
    """
    Pure function to apply delta check results to a canonical product dict.
    Updates price, INR recalculation, availability, and per-variant size stock states.
    Sets shopify_sync_pending = True if changes occurred.
    Strictly enforces selective timestamping (ADR 0008, ADR 0010):
    ONLY stamp last_verified_at if status in ('success', 'not_found').
    Returns (updated_product, has_changed).
    """
    status = delta_result.get("status")
    if status not in ("success", "not_found"):
        # Transient error or rate limited: never mutate product and never stamp timestamp
        return product, False

    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    product["last_verified_at"] = now_iso

    has_changed = False
    price_changed = bool(delta_result.get("price_changed", False))
    stock_changed = bool(delta_result.get("stock_changed", False))
    variant_stock_changed = bool(delta_result.get("variant_stock_changed", False))
    variant_price_changed = bool(delta_result.get("variant_price_changed", False))
    has_changed = price_changed or stock_changed or variant_stock_changed or variant_price_changed

    # 1. Apply price changes
    new_source_price = float(delta_result.get("current_source_price", product.get("source_price", 0.0)) or 0.0)
    if price_changed and new_source_price > 0:
        product["source_price"] = new_source_price
        product["current_price"] = float(round(new_source_price * forex_rate))
        has_changed = True

    new_compare_price = delta_result.get("current_compare_price")
    if new_compare_price is not None and float(new_compare_price) > 0:
        try:
            product["source_compare_at_price"] = float(new_compare_price)
            product["compare_at_price"] = float(round(float(new_compare_price) * forex_rate))
        except (ValueError, TypeError):
            pass

    # 2. Apply availability changes
    if stock_changed or delta_result.get("availability") in ("out_of_stock", "delisted", "in_stock"):
        if "availability" in delta_result:
            if product.get("availability") != delta_result["availability"]:
                has_changed = True
            product["availability"] = delta_result["availability"]
        if "is_active" in delta_result:
            new_is_active = bool(delta_result["is_active"])
            if product.get("is_active") != new_is_active:
                has_changed = True
            product["is_active"] = new_is_active
        else:
            new_is_active = (product.get("availability") == "in_stock")
            if product.get("is_active") != new_is_active:
                has_changed = True
            product["is_active"] = new_is_active

    # 3. Update variant-level states
    variants_delta = delta_result.get("variants_delta", [])
    has_explicit_variant_pricing = any(
        float(v.get("price_usd") or v.get("source_price") or 0.0) > 0 for v in variants_delta if isinstance(v, dict)
    )

    if variants_delta and product.get("variants"):
        var_map = {vd["sku"]: vd for vd in variants_delta if isinstance(vd, dict) and vd.get("sku")}
        for var in product["variants"]:
            if not isinstance(var, dict):
                continue
            v_sku = var.get("sku")
            matched_v = var_map.get(v_sku)
            if matched_v:
                new_stock = bool(matched_v.get("available", matched_v.get("in_stock", False)))
                if var.get("in_stock") != new_stock:
                    var["in_stock"] = new_stock
                    has_changed = True
                if "is_available" in var and var.get("is_available") != new_stock:
                    var["is_available"] = new_stock
                    has_changed = True

                new_v_price = float(matched_v.get("price_usd") or matched_v.get("source_price") or 0.0)
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
            if product.get("availability") != target_avail:
                product["availability"] = target_avail
                has_changed = True
            product["is_active"] = False
            for var in product.get("variants", []):
                if var.get("in_stock") is not False:
                    var["in_stock"] = False
                    has_changed = True
        elif target_avail == "in_stock" and not any(v.get("in_stock", False) for v in product.get("variants", [])):
            if product.get("availability") != "in_stock":
                product["availability"] = "in_stock"
                has_changed = True
            product["is_active"] = True
            for var in product.get("variants", []):
                if var.get("in_stock") is not True:
                    var["in_stock"] = True
                    has_changed = True

    # 4. Delisting handling (ADR 0015)
    if status == "not_found":
        product["is_active"] = False
        product["availability"] = "out_of_stock"
        for v in product.get("variants", []):
            if v.get("in_stock") is not False:
                v["in_stock"] = False
                has_changed = True

    if has_changed:
        product["shopify_sync_pending"] = True
        product["updated_at"] = now_iso

    return product, has_changed
