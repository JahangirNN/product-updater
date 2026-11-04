"""
Store Delta Updater: SEPHORA
Polls live price and stock status for Sephora products using curl_cffi with SSR Redux parsing.
Pure functional composition, zero classes (ADR 0002, ADR 0005, ADR 0006, ADR 0010, ADR 0015, ADR 0021, ADR 0026).
"""
import time
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from parsel import Selector

try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

from storage.rate_limiter import acquire_permit, trip_circuit_breaker, record_throttle, record_success
from storage.forex import convert_usd_to_inr
from stores.sephora.inflow import parse_price_str, clean_text

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def check_price_and_stock(
    product: Dict[str, Any],
    client: Optional[Any] = None,
    store_name: str = "sephora",
    rate_limiter: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Fetch the latest price and stock status for an existing Sephora product.
    Extracts embedded Redux page.product JSON for granular child variant stock.
    Preserves old values on 404 delisting and trips circuit breaker on 429.
    """
    t_start = time.perf_counter()
    resolved_store = store_name or product.get("store") or product.get("source_store") or "sephora"
    handle = product.get("handle") or ""
    old_source_price = float(product.get("source_price") or product.get("source_price_usd") or 0.0)
    old_availability = product.get("availability", "unknown")
    source_url = product.get("source_url", "")

    if not source_url:
        return {
            "status": "error",
            "id": product.get("id"),
            "handle": handle,
            "store": resolved_store,
            "error": "Missing source_url on product record.",
            "elapsed_ms": 0.0,
            "has_changed": False
        }

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

            # 2. Fast HTTP Request via curl_cffi Session
            session = cffi_requests.Session(impersonate="chrome124")
            resp = session.get(
                source_url,
                headers=DEFAULT_HEADERS,
                timeout=25,
                allow_redirects=True
            )
            resp.encoding = "utf-8"
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
            if status_code == 404 or "Product Not Available" in html_content:
                return {
                    "status": "not_found",
                    "id": product.get("id"),
                    "handle": handle,
                    "store": resolved_store,
                    "availability": old_availability,
                    "source_price": old_source_price,
                    "price": str(product.get("current_price", "")),
                    "message": "404 Product not found / delisted.",
                    "elapsed_ms": elapsed_ms,
                    "has_changed": False
                }

            if status_code != 200 or len(html_content) < 5000:
                time.sleep(1.0 * (attempt + 1))
                continue

            # 5. Extract Redux page.product JSON
            sel = Selector(html_content)
            scripts = sel.css("script::text").getall()
            pdata = None
            for s in scripts:
                s_clean = s.strip()
                if s_clean.startswith('{"page":') and '"product":' in s_clean:
                    try:
                        parsed = json.loads(s_clean)
                        pdata = parsed.get("page", {}).get("product")
                        if pdata:
                            break
                    except Exception:
                        pass

            if not pdata:
                time.sleep(1.0 * (attempt + 1))
                continue

            record_success(resolved_store)

            # 6. Parse Variant-Level Stock & Prices
            current_sku = pdata.get("currentSku") or {}
            child_skus = pdata.get("regularChildSkus") or []
            sku_list = child_skus if child_skus else ([current_sku] if current_sku else [])

            variants_delta = []
            for sk in sku_list:
                sk_id = str(sk.get("skuId", "")).strip()
                if not sk_id:
                    continue
                v_price = parse_price_str(sk.get("listPrice"))
                v_in_stock = not bool(sk.get("isOutOfStock", False))
                v_val = clean_text(sk.get("variationValue") or sk.get("displayName") or "")

                variants_delta.append({
                    "sku": sk_id,
                    "title": v_val,
                    "source_price": v_price,
                    "in_stock": v_in_stock
                })

            # Base product source price
            new_price = parse_price_str(current_sku.get("listPrice"))
            if new_price <= 0 and variants_delta:
                new_price = variants_delta[0]["source_price"]
            if new_price <= 0:
                new_price = old_source_price

            # 7. Compute Overall Availability (Active if ANY variant is in stock)
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
                v_delta_map = {vd["sku"]: vd for vd in variants_delta}

                for ev in existing_vars:
                    ev_sku = str(ev.get("sku", "")).strip()
                    matched_vd = v_delta_map.get(ev_sku)

                    if matched_vd:
                        old_v_stock = bool(ev.get("in_stock", True))
                        new_v_stock = bool(matched_vd.get("in_stock", True))
                        if old_v_stock != new_v_stock:
                            variant_stock_changed = True
                            changed_variants.append({
                                "sku": ev_sku,
                                "old_in_stock": old_v_stock,
                                "new_in_stock": new_v_stock
                            })

                        old_v_sp = float(ev.get("source_price") or ev.get("source_price_usd") or 0.0)
                        new_v_sp = float(matched_vd.get("source_price") or 0.0)
                        if new_v_sp > 0 and old_v_sp > 0 and abs(new_v_sp - old_v_sp) > 0.01:
                            variant_price_changed = True
                            changed_variant_prices.append({
                                "sku": ev_sku,
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

    return {
        "status": "error",
        "id": product.get("id"),
        "handle": handle,
        "store": resolved_store,
        "error": "Failed after 3 retry attempts to extract Sephora Redux JSON.",
        "elapsed_ms": (time.perf_counter() - t_start) * 1000,
        "has_changed": False
    }


def apply_delta_to_product(
    product: Dict[str, Any],
    delta_result: Dict[str, Any],
    forex_rate: float = 95.0
) -> Tuple[Dict[str, Any], bool]:
    """
    Apply delta check results to an existing Sephora product record.
    Pure functional mutation: returns (updated_product, has_changed).
    Enforces Whole-Rupee INR pricing (ADR 0006) and Parent-Child Stock Harmony (ADR 0015).
    """
    updated = json.loads(json.dumps(product))  # Deep copy
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    updated["last_verified_at"] = now_iso

    has_changed = False
    new_avail = delta_result.get("availability")
    new_source_price = delta_result.get("source_price")
    variants_delta = delta_result.get("variants_delta") or []

    # 1. Update Availability
    if new_avail and new_avail != updated.get("availability"):
        updated["availability"] = new_avail
        updated["is_active"] = (new_avail == "in_stock")
        has_changed = True

    # 2. Update Source Price and Converted Whole-Rupee INR (ADR 0006)
    if new_source_price is not None and float(new_source_price) > 0:
        old_sp = float(updated.get("source_price") or updated.get("source_price_usd") or 0.0)
        if abs(new_source_price - old_sp) > 0.01:
            updated["source_price"] = new_source_price
            updated["source_price_usd"] = new_source_price
            price_inr = int(round(convert_usd_to_inr(new_source_price, forex_rate)))
            updated["current_price"] = price_inr
            updated["current_price_inr"] = price_inr
            has_changed = True

    # 3. Synchronize Child Variants
    existing_variants = updated.get("variants", [])
    if existing_variants and variants_delta:
        v_delta_map = {vd["sku"]: vd for vd in variants_delta}

        for ev in existing_variants:
            ev_sku = str(ev.get("sku", "")).strip()
            matched_vd = v_delta_map.get(ev_sku)

            if matched_vd:
                # Update variant stock
                vd_stock = bool(matched_vd.get("in_stock", True))
                if ev.get("in_stock") != vd_stock:
                    ev["in_stock"] = vd_stock
                    ev["is_active"] = vd_stock
                    ev["inventory_quantity"] = 10 if vd_stock else 0
                    has_changed = True

                # Update variant price
                vd_sp = matched_vd.get("source_price")
                if vd_sp is not None and vd_sp > 0:
                    old_v_sp = float(ev.get("source_price") or ev.get("source_price_usd") or 0.0)
                    if abs(vd_sp - old_v_sp) > 0.01:
                        ev["source_price"] = vd_sp
                        ev["source_price_usd"] = vd_sp
                        v_price_inr = int(round(convert_usd_to_inr(vd_sp, forex_rate)))
                        ev["price_inr"] = v_price_inr
                        ev["current_price"] = v_price_inr
                        has_changed = True

        updated["variants"] = existing_variants

    # 4. Strict Stock Harmony Invariant (ADR 0015)
    any_variant_in_stock = any(v.get("in_stock", False) for v in updated.get("variants", []))
    if any_variant_in_stock and updated.get("availability") != "in_stock":
        updated["availability"] = "in_stock"
        updated["is_active"] = True
        has_changed = True
    elif not any_variant_in_stock and updated.get("availability") != "out_of_stock":
        updated["availability"] = "out_of_stock"
        updated["is_active"] = False
        has_changed = True

    if has_changed:
        updated["updated_at"] = now_iso

    return updated, has_changed
