"""
Store Delta Updater: COACH
Polls live price and stock status for Coach products using lightweight HTTP PDP fetch and JSON-LD parsing.
Pure functional composition, zero classes (ADR 0002, ADR 0005, ADR 0010).
"""
import time
import random
import json
import re
from typing import Any, Dict, List, Optional, Tuple
import httpx

from storage.network import create_http_client, DEFAULT_BROWSER_HEADERS, get_browser_headers
from storage.rate_limiter import acquire_permit, trip_circuit_breaker, parse_retry_after

DEFAULT_HEADERS = get_browser_headers({"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})


def check_price_and_stock(
    product: Dict[str, Any],
    client: Optional[httpx.Client] = None,
    store_name: str = "coach",
    rate_limiter: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Fetch the latest price and stock status for an existing Coach product.
    Parses JSON-LD (@type Product and ProductGroup) and size swatch buttons.
    Preserves old values on 404 delisting and trips circuit breaker on 429.
    """
    t_start = time.perf_counter()
    resolved_store = store_name or product.get("store") or product.get("source_store") or "coach"
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

            # 2. Execute HTTP fetch
            if client:
                resp = client.get(source_url, headers=DEFAULT_HEADERS, follow_redirects=True)
            else:
                with create_http_client(custom_headers=DEFAULT_HEADERS) as c:
                    resp = c.get(source_url, follow_redirects=True)

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
                    "elapsed_ms": elapsed_ms,
                    "message": "Product delisted (HTTP 404)"
                }

            resp.raise_for_status()

            # 5. Extract price, availability, and variants from HTML & JSON-LD
            html_text = resp.text
            target_sku = product.get("source_sku")
            parsed_info = extract_coach_pdp_info(html_text, target_sku=target_sku)

            current_source_price = parsed_info.get("price") or old_source_price
            current_availability = parsed_info.get("availability") or old_availability
            variants_delta = parsed_info.get("variants_delta", [])

            is_available = current_availability == "in_stock"
            price_changed = abs(current_source_price - old_source_price) > 0.01 if old_source_price > 0 else False
            stock_changed = current_availability != old_availability

            return {
                "status": "success",
                "handle": handle,
                "current_source_price": current_source_price,
                "old_source_price": old_source_price,
                "current_compare_price": parsed_info.get("compare_at_price"),
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


def extract_coach_pdp_info(html_text: str, target_sku: Optional[str] = None) -> Dict[str, Any]:
    """
    Parse Coach HTML to extract current price, overall stock, and variant status.
    If target_sku is provided, precisely pins availability and price to the specific SKU.
    """
    info: Dict[str, Any] = {
        "price": None,
        "compare_at_price": None,
        "availability": "out_of_stock",
        "variants_delta": []
    }

    clean_target_sku = re.sub(r'\s+', ' ', target_sku).strip().lower() if target_sku else ""
    target_found = False

    # 1. Parse JSON-LD blocks
    json_lds = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html_text, re.DOTALL)
    for block in json_lds:
        try:
            d = json.loads(block)
            t = d.get("@type")
            if t == "Product":
                p_sku = d.get("sku", "")
                clean_p_sku = re.sub(r'\s+', ' ', p_sku).strip().lower() if p_sku else ""
                offers = d.get("offers", {})
                if isinstance(offers, list) and offers:
                    offers = offers[0]
                if isinstance(offers, dict):
                    p_price = float(offers.get("price") or 0.0)
                    p_avail = offers.get("availability", "")
                    p_in_stock = "InStock" in p_avail
                    
                    if (clean_target_sku and (clean_p_sku == clean_target_sku or clean_p_sku.startswith(clean_target_sku) or clean_target_sku.startswith(clean_p_sku))) or not target_found:
                        if p_price > 0:
                            info["price"] = p_price
                        info["availability"] = "in_stock" if p_in_stock else "out_of_stock"
                        if clean_target_sku and clean_p_sku == clean_target_sku:
                            target_found = True

            elif t == "ProductGroup":
                variants = d.get("hasVariant", [])
                for v in variants:
                    v_sku = v.get("sku") or ""
                    clean_v_sku = re.sub(r'\s+', ' ', v_sku).strip().lower() if v_sku else ""
                    v_offers = v.get("offers", {})
                    if isinstance(v_offers, list) and v_offers:
                        v_offers = v_offers[0]
                    v_avail = v_offers.get("availability", "")
                    v_in_stock = "InStock" in v_avail
                    v_price = float(v_offers.get("price") or 0.0)
                    info["variants_delta"].append({
                        "sku": v_sku,
                        "available": v_in_stock,
                        "price_usd": v_price
                    })

                    # If target_sku matches this specific variant in ProductGroup
                    if clean_target_sku and (clean_v_sku == clean_target_sku or clean_v_sku.startswith(clean_target_sku) or clean_target_sku.startswith(clean_v_sku)):
                        if v_price > 0:
                            info["price"] = v_price
                        info["availability"] = "in_stock" if v_in_stock else "out_of_stock"
                        target_found = True
        except Exception:
            pass

    # 2. Parse Shoe Size Buttons if present
    # <button class="chakra-button variation-option variation-size css-1bhu9le" data-qa="cm_link_size_swatch_enbld">7</button>
    size_matches = re.findall(r'<button[^>]*class="[^"]*variation-size[^"]*"[^>]*data-qa="([^"]+)"[^>]*>([^<]+)</button>', html_text)
    if size_matches:
        any_in_stock = False
        for data_qa, size_text in size_matches:
            s_clean = size_text.strip()
            in_stock = "enbld" in data_qa.lower()
            if in_stock:
                any_in_stock = True
            info["variants_delta"].append({
                "size": s_clean,
                "available": in_stock
            })
        # For footwear, overall availability is true if ANY size is enabled
        info["availability"] = "in_stock" if any_in_stock else "out_of_stock"

    return info


def extract_handle_from_url(url: str) -> str:
    """Extract product handle from full URL."""
    cleaned = url.split("?")[0].rstrip("/")
    return cleaned.split("/")[-1].replace(".html", "")


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
        return product, False

    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    product["last_verified_at"] = now_iso

    price_changed = bool(delta_result.get("price_changed", False))
    stock_changed = bool(delta_result.get("stock_changed", False))
    has_changed = price_changed or stock_changed

    # Apply price changes
    new_source_price = delta_result.get("current_source_price", product.get("source_price", 0.0))
    if price_changed and new_source_price > 0:
        product["source_price"] = new_source_price
        product["current_price"] = float(round(new_source_price * forex_rate))

    new_compare_price = delta_result.get("current_compare_price")
    if new_compare_price is not None:
        product["compare_at_price"] = float(round(new_compare_price * forex_rate))

    # Apply availability changes
    if stock_changed:
        product["availability"] = delta_result.get("availability", product.get("availability"))
        product["is_active"] = delta_result.get("is_active", product.get("availability") == "in_stock")

    # Update variant states if available
    variants_delta = delta_result.get("variants_delta", [])
    if variants_delta and product.get("variants"):
        sku_map = {re.sub(r'\s+', ' ', v["sku"]).strip().upper(): v for v in variants_delta if v.get("sku")}
        size_map = {str(v["size"]).strip(): v for v in variants_delta if v.get("size")}
        
        variant_modified = False
        for var in product["variants"]:
            v_sku = var.get("sku", "")
            clean_var_sku = re.sub(r'\s+', ' ', v_sku).strip().upper() if v_sku else ""
            
            # 1. Match by SKU (Color Variants or Sized SKUs)
            if clean_var_sku in sku_map:
                v_info = sku_map[clean_var_sku]
                new_stock = bool(v_info.get("available", False))
                if var.get("in_stock") != new_stock:
                    var["in_stock"] = new_stock
                    variant_modified = True

                new_v_price = float(v_info.get("price_usd") or 0.0)
                if new_v_price > 0:
                    old_v_price = float(var.get("source_price") or 0.0)
                    if abs(new_v_price - old_v_price) > 0.01:
                        var["source_price"] = new_v_price
                        var["price"] = f"{round(new_v_price * forex_rate):.2f}"
                        variant_modified = True
            else:
                # 2. Match by Size (Footwear)
                v_title = var.get("title", "")
                for s_key, s_info in size_map.items():
                    if f"US {s_key} " in v_title or v_title == s_key or v_sku.endswith(f"-{s_key}") or v_sku.endswith(f" {s_key} D"):
                        new_stock = bool(s_info.get("available", False))
                        if var.get("in_stock") != new_stock:
                            var["in_stock"] = new_stock
                            variant_modified = True
                        break

        if variant_modified:
            has_changed = True
            # Recalculate top-level availability from variants
            any_var_stock = any(v.get("in_stock", False) for v in product["variants"])
            product["availability"] = "in_stock" if any_var_stock else "out_of_stock"

    if has_changed:
        product["shopify_sync_pending"] = True
        product["updated_at"] = now_iso

    return product, has_changed
