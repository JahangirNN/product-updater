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


def matches_coach_size(s_key: Any, v_title: str, v_sku: str = "") -> bool:
    """
    Match a size string from Coach size buttons (e.g. '7', '7.5', '7D', '8')
    against variant title and SKU with robust support for width suffixes (e.g. 'D', 'B'),
    compound titles like 'US 7D / UK 7D', 'CFZ93 BLK  8   D-7D', etc.
    """
    s_clean = str(s_key or "").strip().upper()
    if not s_clean:
        return False
    t_clean = str(v_title or "").strip().upper()
    k_clean = str(v_sku or "").strip().upper()
    if t_clean == s_clean or k_clean == s_clean:
        return True

    m = re.match(r'^([\d\.]+)([A-Z]*)$', s_clean)
    if m:
        s_num, s_width = m.group(1), m.group(2)
    else:
        s_num, s_width = s_clean, ""

    num_pattern = re.escape(s_num) + r'[A-Z]?(?![.\d])'
    # Check title: e.g. 'US 7D / UK 7D', 'US 7 / UK 5', '7D', '7'
    if re.search(r'(?<![.\d])US\s+' + num_pattern, t_clean):
        return True
    if re.search(r'^' + num_pattern + r'$', t_clean):
        return True
    if re.search(r'(?<![.\d])' + num_pattern + r'\b', t_clean):
        return True

    # Check SKU: e.g. 'CFZ93 BLK  8   D-7D', 'CFX45-7', 'CFX45-7D'
    if re.search(r'[-_\s]' + num_pattern + r'$', k_clean):
        return True
    return False


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
                    "variant_stock_changed": False,
                    "changed_variants": [],
                    "variant_price_changed": False,
                    "changed_variant_prices": [],
                    "variants_delta": [],
                    "elapsed_ms": elapsed_ms,
                    "message": "Product delisted (HTTP 404)"
                }

            resp.raise_for_status()

            # 5. Extract price, availability, and variants from HTML & JSON-LD
            html_text = resp.text
            target_sku = product.get("source_sku")
            parsed_info = extract_coach_pdp_info(html_text, target_sku=target_sku)

            current_source_price = parsed_info.get("price") or old_source_price
            variants_delta = parsed_info.get("variants_delta", [])
            if variants_delta:
                # Ensure granular price_usd is populated across all variants_delta
                if current_source_price > 0:
                    for vd in variants_delta:
                        if isinstance(vd, dict) and float(vd.get("price_usd") or 0.0) <= 0:
                            vd["price_usd"] = current_source_price
                any_var_avail = any(v.get("available") for v in variants_delta if isinstance(v, dict))
                current_availability = "in_stock" if any_var_avail else "out_of_stock"
            else:
                current_availability = parsed_info.get("availability") or old_availability

            is_available = current_availability == "in_stock"
            price_changed = abs(current_source_price - old_source_price) > 0.01 if old_source_price > 0 else False
            stock_changed = current_availability != old_availability

            # Variant delta tracking & interface contract compliance (R1)
            changed_variants = []
            variant_stock_changed = False
            variant_price_changed = False
            changed_variant_prices = []
            if variants_delta and product.get("variants"):
                sku_map = {re.sub(r'\s+', ' ', v["sku"]).strip().upper(): v for v in variants_delta if isinstance(v, dict) and v.get("sku")}
                size_map = {str(v["size"]).strip(): v for v in variants_delta if isinstance(v, dict) and v.get("size")}
                for var in product["variants"]:
                    if not isinstance(var, dict):
                        continue
                    v_sku = var.get("sku", "")
                    clean_var_sku = re.sub(r'\s+', ' ', v_sku).strip().upper() if v_sku else ""
                    old_v_stock = bool(var.get("in_stock", False))
                    old_v_price = float(var.get("source_price") or 0.0)
                    new_v_stock = old_v_stock
                    new_v_price = old_v_price
                    matched = False

                    if clean_var_sku in sku_map:
                        v_info = sku_map[clean_var_sku]
                        new_v_stock = bool(v_info.get("available", False))
                        cand_p = float(v_info.get("price_usd") or 0.0)
                        if cand_p > 0:
                            new_v_price = cand_p
                        matched = True
                    else:
                        v_title = var.get("title", "")
                        for s_key, s_info in size_map.items():
                            if matches_coach_size(s_key, v_title, v_sku):
                                new_v_stock = bool(s_info.get("available", False))
                                cand_p = float(s_info.get("price_usd") or 0.0)
                                if cand_p > 0:
                                    new_v_price = cand_p
                                matched = True
                                break

                    if matched:
                        if new_v_stock != old_v_stock:
                            variant_stock_changed = True
                            changed_variants.append({
                                "sku": v_sku,
                                "old_in_stock": old_v_stock,
                                "new_in_stock": new_v_stock
                            })
                        if new_v_price > 0 and old_v_price > 0 and abs(new_v_price - old_v_price) > 0.01:
                            variant_price_changed = True
                            changed_variant_prices.append({
                                "sku": v_sku,
                                "size": var.get("size") or var.get("title") or "",
                                "old_source_price": old_v_price,
                                "new_source_price": new_v_price
                            })
            elif not variants_delta and product.get("variants") and current_availability in ("out_of_stock", "delisted"):
                for var in product["variants"]:
                    if not isinstance(var, dict):
                        continue
                    old_v_stock = bool(var.get("in_stock", False))
                    if old_v_stock:
                        variant_stock_changed = True
                        changed_variants.append({
                            "sku": var.get("sku", ""),
                            "old_in_stock": True,
                            "new_in_stock": False
                        })

            return {
                "status": "success",
                "handle": handle,
                "current_source_price": current_source_price,
                "old_source_price": old_source_price,
                "new_source_price": current_source_price,
                "current_compare_price": parsed_info.get("compare_at_price"),
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
                        target_found = True

                if info["variants_delta"]:
                    any_group_in_stock = any(v.get("available") for v in info["variants_delta"])
                    info["availability"] = "in_stock" if any_group_in_stock else "out_of_stock"
        except Exception:
            pass

    # 2. Parse Shoe Size Buttons if present
    # <button class="chakra-button variation-option variation-size css-1bhu9le" data-qa="cm_link_size_swatch_enbld">7</button>
    size_btn_pattern = re.compile(
        r'<button([^>]*class="[^"]*variation-size[^"]*"[^>]*)>([\s\S]*?)</button>',
        re.IGNORECASE
    )
    btn_matches = list(size_btn_pattern.finditer(html_text))
    if btn_matches:
        any_in_stock = False
        pdp_price = float(info.get("price") or 0.0)
        for bm in btn_matches:
            btn_attrs = bm.group(1)
            size_text = re.sub(r'<[^>]+>', '', bm.group(2)).strip()
            s_clean = size_text.strip()
            data_qa_m = re.search(r'data-qa="([^"]+)"', btn_attrs, re.IGNORECASE)
            data_qa = data_qa_m.group(1) if data_qa_m else ""
            in_stock = "enbld" in data_qa.lower()
            if in_stock:
                any_in_stock = True

            # Extract button price if present (data-price or inner text), else fallback to PDP price
            btn_price = 0.0
            price_attr_m = re.search(r'data-price="([\d\.]+)"', btn_attrs, re.IGNORECASE)
            if price_attr_m:
                try:
                    btn_price = float(price_attr_m.group(1))
                except ValueError:
                    btn_price = 0.0
            if btn_price <= 0:
                inner_price_m = re.search(r'\$\s*([\d\.]+)', bm.group(2))
                if inner_price_m:
                    try:
                        btn_price = float(inner_price_m.group(1))
                    except ValueError:
                        btn_price = 0.0
            if btn_price <= 0 and pdp_price > 0:
                btn_price = pdp_price

            v_entry: Dict[str, Any] = {
                "size": s_clean,
                "available": in_stock
            }
            if btn_price > 0:
                v_entry["price_usd"] = btn_price
            info["variants_delta"].append(v_entry)
        # For footwear, overall availability is true if ANY size is enabled
        info["availability"] = "in_stock" if any_in_stock else "out_of_stock"

    if info["variants_delta"]:
        any_var_avail = any(v.get("available") for v in info["variants_delta"] if isinstance(v, dict))
        info["availability"] = "in_stock" if any_var_avail else "out_of_stock"

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

    prev_availability = product.get("availability")
    price_changed = bool(delta_result.get("price_changed", False))
    stock_changed = bool(delta_result.get("stock_changed", False))
    variant_stock_changed = bool(delta_result.get("variant_stock_changed", False))
    variant_price_changed = bool(delta_result.get("variant_price_changed", False))
    has_changed = price_changed or stock_changed or variant_stock_changed or variant_price_changed

    # Apply price changes
    new_source_price = float(delta_result.get("current_source_price", product.get("source_price", 0.0)) or 0.0)
    if price_changed and new_source_price > 0:
        product["source_price"] = new_source_price
        product["current_price"] = float(round(new_source_price * forex_rate))

    new_compare_price = delta_result.get("current_compare_price")
    if new_compare_price is not None:
        try:
            product["compare_at_price"] = float(round(float(new_compare_price) * forex_rate))
        except (ValueError, TypeError):
            pass

    # Apply availability changes
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

    # Update variant states if available
    variants_delta = delta_result.get("variants_delta", [])
    variant_modified = False

    has_explicit_variant_pricing = any(
        float(v.get("price_usd") or 0.0) > 0 for v in variants_delta if isinstance(v, dict)
    )

    if variants_delta and product.get("variants"):
        sku_map = {re.sub(r'\s+', ' ', v["sku"]).strip().upper(): v for v in variants_delta if isinstance(v, dict) and v.get("sku")}
        size_map = {str(v["size"]).strip(): v for v in variants_delta if isinstance(v, dict) and v.get("size")}

        for var in product["variants"]:
            if not isinstance(var, dict):
                continue
            v_sku = var.get("sku", "")
            clean_var_sku = re.sub(r'\s+', ' ', v_sku).strip().upper() if v_sku else ""

            matched_v = None
            # 1. Match by SKU (Color Variants or Sized SKUs)
            if clean_var_sku in sku_map:
                matched_v = sku_map[clean_var_sku]
            else:
                # 2. Match by Size (Footwear)
                v_title = var.get("title", "")
                for s_key, s_info in size_map.items():
                    if matches_coach_size(s_key, v_title, v_sku):
                        matched_v = s_info
                        break

            if matched_v:
                new_stock = bool(matched_v.get("available", False))
                if var.get("in_stock") != new_stock:
                    var["in_stock"] = new_stock
                    variant_modified = True
                if "is_available" in var and var.get("is_available") != new_stock:
                    var["is_available"] = new_stock
                    variant_modified = True

                new_v_price = float(matched_v.get("price_usd") or 0.0)
                if new_v_price > 0:
                    old_v_price = float(var.get("source_price") or 0.0)
                    if abs(new_v_price - old_v_price) > 0.01:
                        var["source_price"] = new_v_price
                        var["price"] = f"{round(new_v_price * forex_rate):.2f}"
                        var["price_current"] = float(round(new_v_price * forex_rate))
                        variant_modified = True
                    else:
                        if "price_current" not in var:
                            var["price_current"] = float(round(new_v_price * forex_rate))
                elif price_changed and new_source_price > 0 and not has_explicit_variant_pricing:
                    old_v_price = float(var.get("source_price") or 0.0)
                    if abs(new_source_price - old_v_price) > 0.01:
                        var["source_price"] = new_source_price
                        var["price"] = f"{round(new_source_price * forex_rate):.2f}"
                        var["price_current"] = float(round(new_source_price * forex_rate))
                        variant_modified = True

        # Fallback: if top-level price changed and child variants lack explicit individual prices, uniform sync
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

        # Invariant: Harmonize top-level availability from variants
        any_var_stock = any(v.get("in_stock", False) for v in product["variants"] if isinstance(v, dict))
        expected_avail = "in_stock" if any_var_stock else "out_of_stock"
        if product.get("availability") != expected_avail:
            product["availability"] = expected_avail
            product["is_active"] = (expected_avail == "in_stock")
            has_changed = True

    elif not variants_delta and product.get("variants"):
        if price_changed and new_source_price > 0:
            for var in product["variants"]:
                if isinstance(var, dict):
                    old_v_price = float(var.get("source_price") or 0.0)
                    if abs(new_source_price - old_v_price) > 0.01:
                        var["source_price"] = new_source_price
                        var["price"] = f"{round(new_source_price * forex_rate):.2f}"
                        var["price_current"] = float(round(new_source_price * forex_rate))
                        has_changed = True

        if product.get("availability") in ("out_of_stock", "delisted"):
            # Availability Cascade:
            # When top-level availability flips to "out_of_stock" or delisted, cascade in_stock = False to all child variants when variants_delta is empty.
            product["is_active"] = False
            cascade_modified = False
            for var in product["variants"]:
                if isinstance(var, dict):
                    if var.get("in_stock") is not False:
                        var["in_stock"] = False
                        cascade_modified = True
                    if "is_available" in var and var.get("is_available") is not False:
                        var["is_available"] = False
                        cascade_modified = True
            if cascade_modified:
                has_changed = True
        elif product.get("availability") == "in_stock" and (
            prev_availability in ("out_of_stock", "delisted")
            or not any(v.get("in_stock", False) for v in product["variants"] if isinstance(v, dict))
        ):
            # Restock Cascade:
            # When an out-of-stock or delisted product restocks to "in_stock", cascade in_stock = True to child variants when variants_delta is empty.
            product["is_active"] = True
            cascade_modified = False
            for var in product["variants"]:
                if isinstance(var, dict):
                    if var.get("in_stock") is not True:
                        var["in_stock"] = True
                        cascade_modified = True
                    if "is_available" in var and var.get("is_available") is not True:
                        var["is_available"] = True
                        cascade_modified = True
            if cascade_modified:
                has_changed = True

    if has_changed:
        product["shopify_sync_pending"] = True
        product["updated_at"] = now_iso

    return product, has_changed
