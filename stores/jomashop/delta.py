"""
Store Delta Updater: Jomashop (Luxury & Designer Watches)
Fast, lightweight polling for price and stock availability using Apollo GraphQL endpoint.
Pure functions only, zero classes (ADR 0002, ADR 0005, ADR 0006, ADR 0008, ADR 0010, ADR 0015).
"""
import os
import sys
import time
import random
import re
from typing import Any, Dict, List, Optional, Tuple
import httpx

try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

from storage.network import create_http_client, DEFAULT_BROWSER_HEADERS
from storage.rate_limiter import acquire_permit, trip_circuit_breaker, parse_retry_after

GRAPHQL_URL = "https://www.jomashop.com/graphql"

CHECK_PRICE_STOCK_QUERY_URL_KEY = """
query checkPriceAndStock($urlKey: String!) {
  products(filter: { url_key: { eq: $urlKey } }) {
    items {
      id
      sku
      url_key
      stock_status
      price_range {
        minimum_price {
          regular_price { value currency }
          final_price { value currency }
          msrp_price { value currency }
        }
      }
    }
  }
}
"""

CHECK_PRICE_STOCK_QUERY_SKU = """
query checkPriceAndStockBySku($sku: String!) {
  products(filter: { sku: { eq: $sku } }) {
    items {
      id
      sku
      url_key
      stock_status
      price_range {
        minimum_price {
          regular_price { value currency }
          final_price { value currency }
          msrp_price { value currency }
        }
      }
    }
  }
}
"""


def _post_graphql(
    payload: Dict[str, Any],
    headers: Dict[str, str],
    client: Optional[Any] = None,
    timeout: float = 15.0
) -> Tuple[Optional[Dict[str, Any]], int, str]:
    """
    Execute POST GraphQL request using injected client or curl_cffi Chrome TLS
    impersonation to bypass Cloudflare 493 bot protection at $0.00 / 0 Firecrawl tokens.
    Returns (json_data, status_code, error_message).
    """
    if client is not None:
        try:
            resp = client.post(GRAPHQL_URL, json=payload, headers=headers)
            status = getattr(resp, "status_code", 200)
            if status == 200:
                data = resp.json()
                errors = data.get("errors", []) if isinstance(data, dict) else []
                if errors:
                    for err in errors:
                        cat = str(err.get("extensions", {}).get("category", ""))
                        code = str(err.get("extensions", {}).get("error-code", ""))
                        msg = str(err.get("message", ""))
                        if "bot-protection" in cat or "bot-protection" in code or "Bot Protection" in msg:
                            return None, 493, f"Bot protection triggered: {msg}"
                return data, 200, ""
            return None, status, f"HTTP status {status}"
        except Exception as exc:
            return None, 0, f"Injected client error: {exc}"

    if HAS_CURL_CFFI:
        try:
            resp = cffi_requests.post(
                GRAPHQL_URL,
                json=payload,
                headers=headers,
                impersonate="chrome124",
                timeout=timeout
            )
            status = resp.status_code
            if status == 200:
                try:
                    data = resp.json()
                    errors = data.get("errors", []) if isinstance(data, dict) else []
                    if errors:
                        for err in errors:
                            cat = str(err.get("extensions", {}).get("category", ""))
                            code = str(err.get("extensions", {}).get("error-code", ""))
                            msg = str(err.get("message", ""))
                            if "bot-protection" in cat or "bot-protection" in code or "Bot Protection" in msg:
                                return None, 493, f"Bot protection triggered: {msg}"
                    return data, 200, ""
                except Exception as json_err:
                    return None, 200, f"JSON parse error: {json_err}"
            return None, status, f"HTTP status {status}"
        except Exception as exc:
            return None, 0, f"curl_cffi error: {exc}"

    # Fallback to standard HTTP client
    try:
        with create_http_client(timeout=timeout) as c:
            resp = c.post(GRAPHQL_URL, json=payload, headers=headers)
        status = resp.status_code
        if status == 200:
            data = resp.json()
            return data, 200, ""
        return None, status, f"HTTP status {status}"
    except Exception as exc:
        return None, 0, f"HTTP client error: {exc}"


def extract_url_key(product: Dict[str, Any]) -> str:
    """Extract canonical url_key from product record or source URL."""
    url_key = product.get("url_key")
    if url_key:
        return str(url_key).strip()

    source_url = product.get("source_url") or ""
    if source_url:
        cleaned = source_url.split("?")[0].rstrip("/")
        last_seg = cleaned.split("/")[-1]
        if last_seg.endswith(".html"):
            last_seg = last_seg[:-5]
        if last_seg:
            return last_seg

    handle = product.get("handle")
    if handle:
        return str(handle).strip()

    return ""


def check_price_and_stock(
    product: Dict[str, Any],
    client: Optional[httpx.Client] = None,
    store_name: str = "jomashop",
    rate_limiter: Optional[Any] = None,
    browser_page: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Poll live price and stock status for an existing Jomashop watch product.
    Queries POST https://www.jomashop.com/graphql with Chrome TLS impersonation.
    Applies per-store rate limiting and trips store circuit breaker on HTTP 429/493/403.
    Preserves old_availability and price fields on 404/delisting.
    """
    t_start = time.perf_counter()
    resolved_store = store_name or product.get("store") or product.get("source_store") or "jomashop"
    handle = product.get("handle") or extract_url_key(product)
    url_key = extract_url_key(product)
    source_sku = product.get("source_sku") or ""
    old_source_price = float(product.get("source_price") or 0.0)
    old_availability = product.get("availability", "unknown")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Content-Type": "application/json"
    }

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

            # 2. Issue GraphQL request via Chrome TLS impersonation
            payload = {
                "operationName": "checkPriceAndStock",
                "query": CHECK_PRICE_STOCK_QUERY_URL_KEY,
                "variables": {"urlKey": url_key}
            }

            data, status_code, err_msg = _post_graphql(payload, headers, client=client)
            elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)

            # Handle rate limit (429) or Cloudflare bot protection / challenge (489, 493, 403, 503)
            if status_code in (429, 489, 493, 403, 500, 502, 503, 504):
                jitter = random.uniform(1.0, 2.0 * (2 ** attempt))
                backoff_duration = 3.0 + jitter

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
                        "error": f"Rate limit / bot protection (HTTP {status_code}): {err_msg}"
                    }

            if status_code == 404:
                return {
                    "status": "not_found",
                    "handle": handle,
                    "availability": "out_of_stock",
                    "old_availability": old_availability,
                    "current_source_price": old_source_price,
                    "old_source_price": old_source_price,
                    "new_source_price": old_source_price,
                    "current_compare_price": product.get("source_compare_at_price"),
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

            if status_code != 200 or not data:
                if attempt < 2:
                    time.sleep(1.0 * (2 ** attempt))
                    continue
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
                    "error": f"HTTP {status_code}: {err_msg}"
                }

            items = data.get("data", {}).get("products", {}).get("items", [])

            # If url_key query returned no items, try fallback to SKU if available
            if not items and source_sku:
                fallback_payload = {
                    "operationName": "checkPriceAndStockBySku",
                    "query": CHECK_PRICE_STOCK_QUERY_SKU,
                    "variables": {"sku": source_sku}
                }
                fb_data, fb_status, fb_err = _post_graphql(fallback_payload, headers, client=client)
                if fb_status == 200 and fb_data:
                    items = fb_data.get("data", {}).get("products", {}).get("items", [])

            if not items:
                # Delisted / Not found in catalog
                return {
                    "status": "not_found",
                    "handle": handle,
                    "availability": "out_of_stock",
                    "old_availability": old_availability,
                    "current_source_price": old_source_price,
                    "old_source_price": old_source_price,
                    "new_source_price": old_source_price,
                    "current_compare_price": product.get("source_compare_at_price"),
                    "is_active": False,
                    "price_changed": False,
                    "stock_changed": old_availability != "out_of_stock",
                    "variant_stock_changed": False,
                    "changed_variants": [],
                    "variant_price_changed": False,
                    "changed_variant_prices": [],
                    "variants_delta": [],
                    "elapsed_ms": elapsed_ms,
                    "message": "Product delisted or removed from catalog"
                }

            item = items[0]
            price_range = item.get("price_range", {}).get("minimum_price", {})
            final_p = price_range.get("final_price", {}).get("value")
            regular_p = price_range.get("regular_price", {}).get("value")
            msrp_p = price_range.get("msrp_price", {}).get("value")

            current_source_price = float(final_p or 0.0)
            compare_val = msrp_p or regular_p
            current_compare_price = float(compare_val) if compare_val and float(compare_val) > current_source_price else None

            stock_status = str(item.get("stock_status", "")).upper()
            is_in_stock = (stock_status == "IN_STOCK")
            current_availability = "in_stock" if is_in_stock else "out_of_stock"

            price_changed = abs(current_source_price - old_source_price) > 0.01 if old_source_price > 0 else False
            stock_changed = (current_availability != old_availability)

            # Build variant delta
            item_sku = item.get("sku") or source_sku
            stored_variants = product.get("variants", [])
            variants_delta = []

            for var in stored_variants:
                if not isinstance(var, dict):
                    continue
                v_sku = var.get("sku") or item_sku
                variants_delta.append({
                    "sku": v_sku,
                    "available": is_in_stock,
                    "price_usd": current_source_price
                })

            changed_variants = []
            variant_stock_changed = False
            variant_price_changed = False
            changed_variant_prices = []

            if variants_delta and stored_variants:
                sku_map = {v["sku"]: v for v in variants_delta if v.get("sku")}
                for var in stored_variants:
                    if not isinstance(var, dict):
                        continue
                    v_sku = var.get("sku")
                    old_v_stock = bool(var.get("in_stock", True))
                    if v_sku in sku_map:
                        new_v_stock = bool(sku_map[v_sku].get("available", False))
                        if new_v_stock != old_v_stock:
                            variant_stock_changed = True
                            changed_variants.append({
                                "sku": v_sku,
                                "old_in_stock": old_v_stock,
                                "new_in_stock": new_v_stock
                            })
                        old_v_price = float(var.get("source_price") or 0.0)
                        new_v_price = float(sku_map[v_sku].get("price_usd") or 0.0)
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
                "is_active": is_in_stock,
                "price_changed": price_changed,
                "stock_changed": stock_changed,
                "variant_stock_changed": variant_stock_changed,
                "changed_variants": changed_variants,
                "variant_price_changed": variant_price_changed,
                "changed_variant_prices": changed_variant_prices,
                "variants_delta": variants_delta,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "elapsed_ms": elapsed_ms,
                "message": "Polled successfully via GraphQL"
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
            time.sleep(0.5 * (2 ** attempt))

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
    Pure function to apply delta check results to a Jomashop canonical product dict.
    Updates price, whole-rupee INR recalculation, availability, and variant-level states.
    ONLY stamps last_verified_at when status in ('success', 'not_found').
    Cascades stock depletion on 404 delistings to all child variants (ADR 0015).
    Enforces parent-variant stock harmony.
    Returns (updated_product, has_changed).
    """
    status = delta_result.get("status")
    if status not in ("success", "not_found"):
        # Transient error or rate limited: do NOT mutate and NEVER stamp last_verified_at
        return product, False

    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    product["last_verified_at"] = now_iso

    prev_availability = product.get("availability")
    price_changed = bool(delta_result.get("price_changed", False))
    stock_changed = bool(delta_result.get("stock_changed", False))
    variant_stock_changed = bool(delta_result.get("variant_stock_changed", False))
    variant_price_changed = bool(delta_result.get("variant_price_changed", False))
    has_changed = price_changed or stock_changed or variant_stock_changed or variant_price_changed

    # Handle 404 / delisting cascade (ADR 0015)
    if status == "not_found":
        if product.get("availability") != "out_of_stock":
            has_changed = True
        product["availability"] = "out_of_stock"
        product["is_active"] = False

        if product.get("variants"):
            for var in product["variants"]:
                if isinstance(var, dict) and var.get("in_stock", True):
                    var["in_stock"] = False
                    if "is_available" in var:
                        var["is_available"] = False
                    has_changed = True

        if has_changed:
            product["shopify_sync_pending"] = True
            product["updated_at"] = now_iso

        return product, has_changed

    # Update top-level pricing
    new_source_price = float(delta_result.get("current_source_price", product.get("source_price", 0.0)) or 0.0)
    if (price_changed or new_source_price != product.get("source_price")) and new_source_price > 0:
        product["source_price"] = new_source_price
        product["current_price"] = float(round(new_source_price * forex_rate))

    new_compare_price = delta_result.get("current_compare_price")
    if new_compare_price is not None:
        try:
            product["compare_at_price"] = float(round(float(new_compare_price) * forex_rate))
        except (ValueError, TypeError):
            pass

    # Update top-level availability
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

    # Update child variants
    raw_variants_delta = delta_result.get("variants_delta", [])
    variants_delta = {}
    if isinstance(raw_variants_delta, list):
        variants_delta = {v["sku"]: v for v in raw_variants_delta if isinstance(v, dict) and v.get("sku")}
    elif isinstance(raw_variants_delta, dict):
        variants_delta = raw_variants_delta

    if variants_delta and product.get("variants"):
        variant_modified = False
        has_explicit_variant_pricing = any(
            float(v.get("price_usd") or 0.0) > 0 for v in variants_delta.values() if isinstance(v, dict)
        )

        for var in product["variants"]:
            if not isinstance(var, dict):
                continue
            sku = var.get("sku")
            if sku in variants_delta:
                v_info = variants_delta[sku]
                new_avail = bool(v_info.get("available", False))
                if var.get("in_stock") != new_avail:
                    var["in_stock"] = new_avail
                    variant_modified = True
                if "is_available" in var and var.get("is_available") != new_avail:
                    var["is_available"] = new_avail
                    variant_modified = True

                if v_info.get("price_usd", 0) > 0:
                    new_v_price = float(v_info["price_usd"])
                    old_v_price = float(var.get("source_price") or 0.0)
                    if abs(new_v_price - old_v_price) > 0.01:
                        var["source_price"] = new_v_price
                        var["price"] = f"{round(new_v_price * forex_rate):.2f}"
                        var["price_current"] = float(round(new_v_price * forex_rate))
                        variant_modified = True
                    else:
                        if "price_current" not in var:
                            var["price_current"] = float(round(new_v_price * forex_rate))
                        if "source_price" not in var:
                            var["source_price"] = new_v_price

        # Uniform fallback sync when parent price changed and variants lack explicit individual pricing
        if price_changed and new_source_price > 0 and not has_explicit_variant_pricing:
            for var in product["variants"]:
                if isinstance(var, dict):
                    old_v_price = float(var.get("source_price") or 0.0)
                    if abs(new_source_price - old_v_price) > 0.01:
                        var["source_price"] = new_source_price
                        var["price"] = f"{round(new_source_price * forex_rate):.2f}"
                        var["price_current"] = float(round(new_source_price * forex_rate))
                        variant_modified = True

        if variant_modified:
            has_changed = True

    elif not variants_delta and product.get("variants"):
        if (price_changed or abs(new_source_price - float(product.get("source_price") or 0.0)) > 0.01) and new_source_price > 0:
            for var in product.get("variants", []):
                if isinstance(var, dict):
                    old_v_price = float(var.get("source_price") or 0.0)
                    if abs(new_source_price - old_v_price) > 0.01:
                        var["source_price"] = new_source_price
                        var["price"] = f"{round(new_source_price * forex_rate):.2f}"
                        var["price_current"] = float(round(new_source_price * forex_rate))
                        has_changed = True

    # Harmonize parent availability with child variants (Stock Harmony ADR 0015)
    if product.get("variants"):
        has_any_stock = any(bool(v.get("in_stock", False)) for v in product["variants"] if isinstance(v, dict))
        expected_avail = "in_stock" if has_any_stock else "out_of_stock"
        if product.get("availability") != expected_avail:
            product["availability"] = expected_avail
            product["is_active"] = has_any_stock
            has_changed = True

    if has_changed:
        product["shopify_sync_pending"] = True
        product["updated_at"] = now_iso

    return product, has_changed
