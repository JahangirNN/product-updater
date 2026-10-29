"""
Store Delta Updater: KATE SPADE OUTLET
Polls live price and stock status for Kate Spade products using lightweight HTTP PDP fetch and JSON-LD parsing.
Pure functional composition, zero classes (ADR 0002, ADR 0005, ADR 0010, ADR 0015, ADR 0026).
"""
import time
import random
import json
import re
from typing import Any, Dict, List, Optional, Tuple
import httpx

try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

from storage.network import create_http_client, DEFAULT_BROWSER_HEADERS, get_browser_headers
from storage.rate_limiter import acquire_permit, trip_circuit_breaker, parse_retry_after, record_throttle, record_success
from storage.forex import convert_usd_to_inr
from storage.pricing_engine import resolve_storefront_pricing

DEFAULT_HEADERS = get_browser_headers({"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})


def check_price_and_stock(
    product: Dict[str, Any],
    client: Optional[httpx.Client] = None,
    store_name: str = "katespade",
    rate_limiter: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Fetch the latest price and stock status for an existing Kate Spade product.
    Parses JSON-LD (@type Product and ProductGroup) for variant and parent availability.
    Preserves old values on 404 delisting and trips circuit breaker on 429.
    """
    t_start = time.perf_counter()
    resolved_store = store_name or product.get("store") or product.get("source_store") or "katespade"
    handle = product.get("handle") or ""
    old_source_price = float(product.get("source_price") or 0.0)
    old_availability = product.get("availability", "unknown")
    source_url = product.get("source_url", "")

    for attempt in range(3):
        try:
            # 1. Acquire rate limiter permit
            if rate_limiter and callable(getattr(rate_limiter, "acquire_permit", None)):
                try:
                    rate_limiter.acquire_permit(resolved_store)
                except TypeError:
                    rate_limiter.acquire_permit()
            else:
                acquire_permit(resolved_store)

            # 2. Fast HTTP Request via curl_cffi or httpx
            html_content = ""
            status_code = 0
            
            if HAS_CURL_CFFI:
                req_headers = dict(DEFAULT_HEADERS)
                req_headers["Accept-Language"] = "en-US,en;q=0.9"
                resp = cffi_requests.get(
                    source_url,
                    headers=req_headers,
                    impersonate="chrome124",
                    timeout=15,
                    allow_redirects=True
                )
                status_code = resp.status_code
                html_content = resp.text
            else:
                c = client or create_http_client(headers=DEFAULT_HEADERS, timeout=12.0)
                resp = c.get(source_url, follow_redirects=True)
                status_code = resp.status_code
                html_content = resp.text

            elapsed_ms = (time.perf_counter() - t_start) * 1000

            # 3. Handle Rate Limiting / 429
            if status_code in (429, 503):
                wait_sec = 30.0
                trip_circuit_breaker(resolved_store, wait_sec)
                record_throttle(resolved_store)
                return {
                    "status": "rate_limited",
                    "id": product.get("id"),
                    "handle": handle,
                    "store": resolved_store,
                    "message": f"HTTP {status_code} - rate limited. Circuit breaker tripped.",
                    "elapsed_ms": elapsed_ms,
                    "has_changed": False
                }

            # 4. Handle Delisting / 404
            if status_code == 404:
                return {
                    "status": "not_found",
                    "id": product.get("id"),
                    "handle": handle,
                    "store": resolved_store,
                    "availability": old_availability,
                    "source_price": old_source_price,
                    "price": str(product.get("current_price", "")),
                    "message": f"404 Product not found / delisted.",
                    "elapsed_ms": elapsed_ms,
                    "has_changed": False
                }

            if status_code != 200 or len(html_content) < 1000:
                return {
                    "status": "error",
                    "id": product.get("id"),
                    "handle": handle,
                    "store": resolved_store,
                    "error": f"HTTP status {status_code}, length: {len(html_content)}",
                    "elapsed_ms": elapsed_ms,
                    "has_changed": False
                }

            record_success(resolved_store)

            # 5. Extract JSON-LD Blocks
            json_ld_blocks = extract_json_ld_blocks(html_content)
            product_group = None
            product_obj = None

            for b in json_ld_blocks:
                if isinstance(b, dict):
                    if b.get("@type") == "ProductGroup":
                        product_group = b
                    elif b.get("@type") == "Product":
                        product_obj = b

            new_price = old_source_price
            variants_delta = []

            # 6. Parse Variant-Level Stock & Prices from ProductGroup
            if product_group and "hasVariant" in product_group:
                for v in product_group["hasVariant"]:
                    v_sku = v.get("sku") or ""
                    v_color = v.get("color") or v.get("name") or ""
                    offers = v.get("offers", {})
                    if isinstance(offers, list) and offers:
                        offers = offers[0]
                    v_price = float(offers.get("price") or 0.0) if offers.get("price") else None
                    v_avail = "instock" in str(offers.get("availability", "InStock")).lower()
                    variants_delta.append({
                        "sku": v_sku,
                        "color": v_color,
                        "source_price": v_price,
                        "in_stock": v_avail
                    })
                if variants_delta:
                    # Parent source price matches first available variant
                    valid_prices = [vd["source_price"] for vd in variants_delta if vd.get("source_price")]
                    if valid_prices:
                        new_price = valid_prices[0]

            # Fallback to single Product object if ProductGroup missing
            if not variants_delta and product_obj:
                offers = product_obj.get("offers", {})
                if isinstance(offers, list) and offers:
                    offers = offers[0]
                if offers.get("price"):
                    new_price = float(offers["price"])
                p_avail = "instock" in str(offers.get("availability", "InStock")).lower()
                variants_delta.append({
                    "sku": product_obj.get("sku", ""),
                    "color": "Standard",
                    "source_price": new_price,
                    "in_stock": p_avail
                })

            # 7. Compute Overall Availability (Active if ANY variant is InStock)
            if variants_delta:
                new_availability = "in_stock" if any(vd["in_stock"] for vd in variants_delta) else "out_of_stock"
            else:
                new_availability = old_availability

            price_changed = abs(new_price - old_source_price) > 0.01 if (new_price and old_source_price) else False
            stock_changed = (new_availability != old_availability)

            # 8. Variant-level change detection (ADR 0015, ADR 0021)
            variant_stock_changed = False
            variant_price_changed = False
            changed_variants = []
            changed_variant_prices = []

            existing_vars = product.get("variants", [])
            if existing_vars and variants_delta:
                v_delta_map = {vd["sku"].strip().upper(): vd for vd in variants_delta if vd.get("sku")}
                v_delta_color_map = {vd["color"].strip().title(): vd for vd in variants_delta if vd.get("color")}

                for ev in existing_vars:
                    matched_vd = None
                    ev_sku = ev.get("sku", "").strip().upper()
                    ev_opt1 = ev.get("option1", "").strip().title()
                    ev_title = ev.get("title", "").strip().title()

                    if ev_sku in v_delta_map:
                        matched_vd = v_delta_map[ev_sku]
                    elif ev_opt1 in v_delta_color_map:
                        matched_vd = v_delta_color_map[ev_opt1]
                    elif ev_title in v_delta_color_map:
                        matched_vd = v_delta_color_map[ev_title]

                    if matched_vd:
                        old_v_stock = bool(ev.get("in_stock", True))
                        new_v_stock = bool(matched_vd.get("in_stock", True))
                        if old_v_stock != new_v_stock:
                            variant_stock_changed = True
                            changed_variants.append({
                                "sku": ev.get("sku", ""),
                                "old_in_stock": old_v_stock,
                                "new_in_stock": new_v_stock
                            })

                        old_v_sp = float(ev.get("source_price") or 0.0)
                        new_v_sp = matched_vd.get("source_price")
                        if new_v_sp is not None and new_v_sp > 0 and old_v_sp > 0 and abs(new_v_sp - old_v_sp) > 0.01:
                            variant_price_changed = True
                            changed_variant_prices.append({
                                "sku": ev.get("sku", ""),
                                "title": ev.get("title", ""),
                                "old_source_price": old_v_sp,
                                "new_source_price": new_v_sp
                            })

            has_changed = (price_changed or stock_changed or variant_stock_changed or variant_price_changed)

            return {
                "status": "success",
                "id": product.get("id"),
                "handle": handle,
                "store": resolved_store,
                "availability": new_availability,
                "old_availability": old_availability,
                "source_price": new_price,
                "current_source_price": new_price,
                "new_source_price": new_price,
                "old_source_price": old_source_price,
                "has_changed": has_changed,
                "price_changed": price_changed,
                "stock_changed": stock_changed,
                "variant_stock_changed": variant_stock_changed,
                "changed_variants": changed_variants,
                "variant_price_changed": variant_price_changed,
                "changed_variant_prices": changed_variant_prices,
                "variants_delta": variants_delta,
                "elapsed_ms": elapsed_ms
            }

        except Exception as exc:
            if attempt == 2:
                return {
                    "status": "error",
                    "id": product.get("id"),
                    "handle": handle,
                    "store": resolved_store,
                    "error": str(exc),
                    "elapsed_ms": (time.perf_counter() - t_start) * 1000,
                    "has_changed": False
                }
            time.sleep(1.0)


def extract_json_ld_blocks(html: str) -> List[Dict[str, Any]]:
    """Extract and parse all JSON-LD blocks from HTML."""
    blocks = []
    matches = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
    for m in matches:
        content = m.strip()
        if not content:
            continue
        try:
            data = json.loads(content)
            if isinstance(data, list):
                blocks.extend([d for d in data if isinstance(d, dict)])
            elif isinstance(data, dict):
                blocks.append(data)
        except Exception:
            pass
    return blocks


def apply_delta_to_product(
    product: Dict[str, Any],
    delta_result: Dict[str, Any],
    forex_rate: float = 95.0
) -> Tuple[Dict[str, Any], bool]:
    """
    Apply delta check results to an existing Kate Spade product record.
    Pure functional mutation: returns (updated_product, has_changed).
    Implements ADR 0015 Parent-to-Child Stock Cascades.
    """
    updated = dict(product)
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    updated["last_verified_at"] = now_iso

    has_changed = False
    new_avail = delta_result.get("availability")
    new_source_price = delta_result.get("source_price")
    variants_delta = delta_result.get("variants_delta") or []

    # 1. Update Availability
    if new_avail and new_avail != updated.get("availability"):
        updated["availability"] = new_avail
        has_changed = True

    # 2. Update Source Price and Converted INR
    if new_source_price is not None and float(new_source_price) > 0:
        old_sp = float(updated.get("source_price") or 0.0)
        if abs(new_source_price - old_sp) > 0.01:
            updated["source_price"] = new_source_price
            price_inr = convert_usd_to_inr(new_source_price, forex_rate)
            updated["current_price"] = price_inr
            has_changed = True

    # 3. Synchronize Child Variants
    existing_variants = list(updated.get("variants", []))
    if existing_variants and variants_delta:
        v_delta_map = {vd["sku"].strip().upper(): vd for vd in variants_delta if vd.get("sku")}
        v_delta_color_map = {vd["color"].strip().title(): vd for vd in variants_delta if vd.get("color")}

        for ev in existing_variants:
            matched_vd = None
            ev_sku = ev.get("sku", "").strip().upper()
            ev_opt1 = ev.get("option1", "").strip().title()
            ev_title = ev.get("title", "").strip().title()

            if ev_sku in v_delta_map:
                matched_vd = v_delta_map[ev_sku]
            elif ev_opt1 in v_delta_color_map:
                matched_vd = v_delta_color_map[ev_opt1]
            elif ev_title in v_delta_color_map:
                matched_vd = v_delta_color_map[ev_title]

            if matched_vd:
                # Update variant stock
                vd_stock = matched_vd.get("in_stock", True)
                if ev.get("in_stock") != vd_stock:
                    ev["in_stock"] = vd_stock
                    ev["inventory_quantity"] = 10 if vd_stock else 0
                    has_changed = True

                # Update variant price
                vd_sp = matched_vd.get("source_price")
                if vd_sp is not None and vd_sp > 0:
                    if abs(vd_sp - float(ev.get("source_price") or 0.0)) > 0.01:
                        ev["source_price"] = vd_sp
                        ev["price"] = str(convert_usd_to_inr(vd_sp, forex_rate))
                        has_changed = True

        updated["variants"] = existing_variants

    # 4. ADR 0015 Availability Cascade Guard
    # If overall availability is out_of_stock and variants_delta had no active items, cascade to all child variants
    if updated.get("availability") == "out_of_stock":
        for ev in updated.get("variants", []):
            if ev.get("in_stock"):
                ev["in_stock"] = False
                ev["inventory_quantity"] = 0
                has_changed = True
    elif updated.get("availability") == "in_stock":
        # Ensure at least one variant is active
        if not any(ev.get("in_stock") for ev in updated.get("variants", [])):
            if updated.get("variants"):
                updated["variants"][0]["in_stock"] = True
                updated["variants"][0]["inventory_quantity"] = 10
                has_changed = True

    return updated, has_changed
