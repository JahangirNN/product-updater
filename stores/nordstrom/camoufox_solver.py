"""
Camoufox Stealth Kasada Solver for Nordstrom (Pure Functions, ADR 0005, ADR 0010)
Solves Kasada cryptographic proof-of-work challenges locally with zero external API fees.
Extracts live price and stock availability directly from Nordstrom PDP JSON-LD.
"""
import time
import json
import re
from typing import Dict, Any, Optional
from camoufox.sync_api import Camoufox


def create_nordstrom_browser(headless: bool = True):
    """Instantiate a Camoufox stealth browser instance."""
    return Camoufox(headless=headless)


def setup_camoufox_route_blocking(page: Any) -> None:
    """
    Attach route filter to Camoufox page to block images, media, fonts, stylesheets,
    and third-party trackers, keeping only primary scripts and documents needed for Kasada + React.
    """
    def _route_filter(route):
        rt = route.request.resource_type
        u = route.request.url.lower()
        if rt in ["image", "media", "font"]:
            route.abort()
        elif any(k in u for k in ["analytics", "tracking", "doubleclick", "google-analytics", "quantummetric", "branch.io", "facebook"]):
            route.abort()
        else:
            route.continue_()

    try:
        page.route("**/*", _route_filter)
    except Exception:
        pass


def fetch_collection_catalog(page: Any) -> Dict[str, Dict[str, Any]]:
    """
    Harvest live price and stock status for the entire On shoe catalog from Nordstrom collection search pages.
    Extracts all products from window.__INITIAL_CONFIG__ in only 2 page navigations (~40s total).
    Returns mapping keyed by style ID and webPathAlias.
    """
    collection_urls = [
        "https://www.nordstrom.com/sr?origin=keywordsearch&keyword=on%20shoes&filterByBrand=on&filterByGenderAge=men&filterByGenderAge=unisex&filterByGenderAge=women&page=1",
        "https://www.nordstrom.com/sr?origin=keywordsearch&keyword=on%20shoes&filterByBrand=on&filterByGenderAge=men&filterByGenderAge=unisex&filterByGenderAge=women&page=2"
    ]
    catalog: Dict[str, Dict[str, Any]] = {}

    for c_url in collection_urls:
        try:
            page.goto(c_url, wait_until="domcontentloaded", timeout=45000)
            for _ in range(12):
                page.wait_for_timeout(1000)
                html = page.content()
                if "istlWas" not in html and len(html) > 20000:
                    break

            idx = html.find("window.__INITIAL_CONFIG__ =")
            if idx == -1:
                continue

            raw_sub = html[idx + len("window.__INITIAL_CONFIG__ ="):].strip()
            decoder = json.JSONDecoder()
            config_data, _ = decoder.raw_decode(raw_sub)
            p_by_id = config_data.get("productResults", {}).get("productsById", {})

            for st_id, p_obj in p_by_id.items():
                props = p_obj.get("propositions", [])
                prop0 = props[0] if props else {}
                avail_data = prop0.get("availability", {})
                ship_qty = int(avail_data.get("shipQuantity", 0) or 0)
                salability = prop0.get("salability", {}).get("status", "")

                retail_range = prop0.get("sellingRetailPriceRange", {})
                base_range = prop0.get("baseRetailPriceRange", {})

                min_p = float(retail_range.get("min", 0.0)) if retail_range.get("min") else 0.0
                max_p = float(retail_range.get("max", 0.0)) if retail_range.get("max") else min_p
                comp_p = float(base_range.get("max", 0.0)) if base_range.get("max") else max_p

                in_stock = (ship_qty > 0) and (salability == "SELLABLE")
                handle_alias = p_obj.get("webPathAlias") or ""

                entry = {
                    "style_id": str(st_id),
                    "handle": handle_alias,
                    "title": p_obj.get("copyProductTitle"),
                    "price_min": min_p,
                    "price_max": max_p,
                    "compare_price": comp_p,
                    "ship_quantity": ship_qty,
                    "salability": salability,
                    "in_stock": in_stock
                }
                catalog[str(st_id)] = entry
                if handle_alias:
                    catalog[handle_alias] = entry
        except Exception:
            continue

    return catalog


def extract_product_from_html(html: str, target_handle: str = "") -> Optional[Dict[str, Any]]:
    """
    Extract product details from HTML, prioritizing primary JSON-LD product block.
    Filters out recommended product carousels (e.g. minidresses).
    """
    title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
    page_title = title_match.group(1).strip() if title_match else ""

    # Check for sold out markers in page title or content
    is_explicitly_sold_out = "sold out" in page_title.lower() or bool(re.search(r'\b(?:sold out|currently unavailable)\b', html, re.I))

    # 1. Search JSON-LD scripts
    scripts = re.findall(r'<script[^>]+type=[\'"]application/ld\+json[\'"][^>]*>(.*?)</script>', html, re.DOTALL)
    candidates = []
    for s in scripts:
        try:
            data = json.loads(s.strip())
            if data.get("@type") == "Product":
                candidates.append(data)
        except Exception:
            continue

    primary_product = None
    if candidates:
        # If multiple, find the one matching On / Shoes / target handle
        cleaned_handle = target_handle.replace("-", " ").lower()
        for c in candidates:
            c_name = (c.get("name") or "").lower()
            c_brand = ""
            if isinstance(c.get("brand"), dict):
                c_brand = c.get("brand", {}).get("name", "").lower()
            elif isinstance(c.get("brand"), str):
                c_brand = c.get("brand", "").lower()

            # Prefer brand "on" or matching title
            if "on" in c_brand or "on" in c_name or any(w in c_name for w in cleaned_handle.split() if len(w) > 3):
                primary_product = c
                break
        if not primary_product:
            primary_product = candidates[0]

    if primary_product:
        name = primary_product.get("name")
        offers = primary_product.get("offers", {})
        low = offers.get("lowPrice") or offers.get("price")
        high = offers.get("highPrice") or low
        avail = offers.get("availability", "")
        is_in_stock = ("InStock" in avail) and not is_explicitly_sold_out
        try:
            price_val = float(low) if low is not None else 0.0
        except (ValueError, TypeError):
            price_val = 0.0

        return {
            "title": name,
            "price_usd": price_val,
            "high_price_usd": float(high) if high is not None else price_val,
            "availability": "in_stock" if is_in_stock else "out_of_stock"
        }

    # 2. Fallback: DOM regex parsing if JSON-LD missing
    if page_title and "nordstrom" in page_title.lower():
        price_match = re.search(r'\$(\d+(?:\.\d{2})?)', html)
        price_val = float(price_match.group(1)) if price_match else 0.0
        return {
            "title": page_title.split("|")[0].strip(),
            "price_usd": price_val,
            "high_price_usd": price_val,
            "availability": "out_of_stock" if is_explicitly_sold_out else "in_stock"
        }

    return None


def extract_size_availability(html: str) -> Dict[str, bool]:
    """
    Extract per-size availability mapping from window.__INITIAL_CONFIG__ in Nordstrom HTML.
    Returns lookup mapping normalized size (and size+color) to boolean stock status.
    """
    idx = html.find("window.__INITIAL_CONFIG__ =")
    if idx == -1:
        return {}
    raw_sub = html[idx + len("window.__INITIAL_CONFIG__ ="):].strip()
    try:
        decoder = json.JSONDecoder()
        config_data, _ = decoder.raw_decode(raw_sub)
    except Exception:
        return {}

    def norm_size(s: str) -> str:
        m = re.search(r'(\d+(?:\.5)?)', s)
        return m.group(1) if m else s.strip().lower()

    size_stock = {}
    displays = config_data.get("productDisplay", {}).get("productDisplaysById", {}).get("entities", {})
    for _, entity in displays.items():
        core_prods = entity.get("coreProducts") or []
        for cp in core_prods:
            choices = cp.get("coreChoices") or []
            for choice in choices:
                c_name = choice.get("displayColorDescription", "").strip().lower()
                for it in choice.get("items", []):
                    sku_data = it.get("sku") or {}
                    sz_raw = it.get("concatenatedDisplaySize") or it.get("sizeDimension1", {}).get("label") or ""
                    sz_norm = norm_size(sz_raw)
                    props = sku_data.get("propositions") or []
                    ship_qty = props[0].get("availability", {}).get("shipQuantity", 0) if props else 0
                    is_avail = ship_qty > 0

                    size_stock[(sz_norm, c_name)] = is_avail
                    if sz_norm not in size_stock or is_avail:
                        size_stock[sz_norm] = is_avail

    return size_stock


def extract_full_pdp_matrix(html: str) -> Optional[Dict[str, Any]]:
    """
    Extract complete multi-colorway product matrix from window.__INITIAL_CONFIG__ in Nordstrom PDP HTML.
    Includes all coreChoices (colorways, high-res images, per-size items with exact selling price, base price, and shipQuantity).
    """
    idx = html.find("window.__INITIAL_CONFIG__ =")
    if idx == -1:
        return None
    raw_sub = html[idx + len("window.__INITIAL_CONFIG__ ="):].strip()
    try:
        decoder = json.JSONDecoder()
        config_data, _ = decoder.raw_decode(raw_sub)
    except Exception:
        return None

    displays = config_data.get("productDisplay", {}).get("productDisplaysById", {}).get("entities", {})
    if not displays:
        return None

    for style_id_key, entity in displays.items():
        core_prods = entity.get("coreProducts") or []
        if not core_prods:
            continue

        raw_title = entity.get("productDescription") or entity.get("copyProductTitle") or ""
        brand = entity.get("sellingBrand") or "On"
        gender = entity.get("gender") or "Unisex"
        item_num = entity.get("itemNumber") or ""
        materials = entity.get("materialsAndCare") or ""

        colorways = []
        for cp in core_prods:
            choices = cp.get("coreChoices") or []
            for ch in choices:
                c_name = ch.get("displayColorDescription", "").strip()
                if not c_name:
                    continue
                c_code = ch.get("colorCode", "")
                ordered_shots = ch.get("orderedShots") or []
                c_images = []
                for shot in ordered_shots:
                    if shot.get("shotName") != "swatch" and shot.get("imageUrl"):
                        u = shot.get("imageUrl")
                        if "?crop=" not in u:
                            u = f"{u}?crop=pad&trim=color"
                        c_images.append(u)

                c_sizes = []
                for it in ch.get("items", []):
                    sku_data = it.get("sku") or {}
                    sz_raw = it.get("concatenatedDisplaySize") or it.get("sizeDimension1", {}).get("label") or ""
                    props = sku_data.get("propositions") or [{}]
                    prop0 = props[0] if props else {}
                    ship_qty = int(prop0.get("availability", {}).get("shipQuantity", 0) or 0)
                    salability = prop0.get("salability", {}).get("status", "")
                    is_sellable = (ship_qty > 0) and (salability == "SELLABLE")

                    pricings = prop0.get("pricings") or [{}]
                    pricing0 = pricings[0] if pricings else {}
                    selling_p = float(pricing0.get("sellingRetail", {}).get("price", 0.0) or 0.0)
                    base_p = float(pricing0.get("baseRetail", {}).get("price", 0.0) or 0.0)

                    c_sizes.append({
                        "us_size": sz_raw,
                        "in_stock": is_sellable,
                        "ship_quantity": ship_qty,
                        "price_usd": selling_p,
                        "compare_price_usd": base_p if base_p > selling_p else None,
                        "sku_id": str(sku_data.get("id", ""))
                    })

                colorways.append({
                    "color_name": c_name,
                    "color_code": c_code,
                    "images": c_images,
                    "featured_image": c_images[0] if c_images else None,
                    "sizes": c_sizes
                })

        return {
            "style_id": str(style_id_key),
            "title": raw_title,
            "brand": brand,
            "gender": gender,
            "item_number": item_num,
            "materials": materials,
            "colorways": colorways
        }

    return None


def solve_and_extract_pdp(page: Any, url: str, target_handle: str = "") -> Dict[str, Any]:
    """
    Navigate to Nordstrom PDP using active Camoufox page, resolve Kasada proof-of-work,
    and extract live price, overall availability, and per-size variant inventory.
    """
    t_start = time.perf_counter()
    try:
        resp = page.goto(url, wait_until="domcontentloaded", timeout=45000)
        status_code = resp.status if resp else 0

        if status_code == 404:
            elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
            return {
                "status": "not_found",
                "availability": "out_of_stock",
                "price_usd": 0.0,
                "size_stock": {},
                "full_matrix": None,
                "elapsed_ms": elapsed_ms,
                "message": "Product page returned HTTP 404"
            }

        # Ensure route blocking is active
        setup_camoufox_route_blocking(page)

        html = ""
        try:
            html = page.content()
        except Exception:
            pass

        for _ in range(20):  # up to 20 x 1000ms = 20s max
            page.wait_for_timeout(1000)
            try:
                html = page.content()
            except Exception:
                continue
            try:
                page_title = page.title().strip()
            except Exception:
                page_title = ""
            if "istlWas" not in html and ("productDisplay" in html or ("__INITIAL_CONFIG__" in html and "coreProducts" in html)):
                break

        # Check if still blocked
        if not page_title:
            try:
                page_title = page.title().strip()
            except Exception:
                page_title = ""

        if "istlWas" in html or not page_title:
            elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
            return {
                "status": "blocked",
                "availability": "in_stock",
                "price_usd": 0.0,
                "size_stock": {},
                "full_matrix": None,
                "elapsed_ms": elapsed_ms,
                "error": "Kasada challenge unresolved after proof-of-work window"
            }

        # Extract product details and per-size stock
        product_data = extract_product_from_html(html, target_handle=target_handle)
        size_stock = extract_size_availability(html)
        full_matrix = extract_full_pdp_matrix(html)
        elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)

        if product_data or full_matrix:
            title = (full_matrix.get("title") if full_matrix else None) or (product_data.get("title") if product_data else "")
            price_usd = (product_data.get("price_usd") if product_data else 0.0)
            high_price_usd = (product_data.get("high_price_usd") if product_data else price_usd)
            
            avail = "out_of_stock"
            if product_data and product_data.get("availability") == "in_stock":
                avail = "in_stock"
            elif full_matrix and any(s.get("in_stock") for cw in full_matrix.get("colorways", []) for s in cw.get("sizes", [])):
                avail = "in_stock"

            return {
                "status": "success",
                "title": title,
                "price_usd": price_usd,
                "high_price_usd": high_price_usd,
                "availability": avail,
                "size_stock": size_stock,
                "full_matrix": full_matrix,
                "elapsed_ms": elapsed_ms
            }

        # Check if page is sold out or delisted
        page_title = page.title()
        if "sold out" in page_title.lower():
            return {
                "status": "success",
                "title": page_title.split("|")[0].strip(),
                "price_usd": 0.0,
                "availability": "out_of_stock",
                "size_stock": {},
                "full_matrix": None,
                "elapsed_ms": elapsed_ms
            }

        return {
            "status": "error",
            "availability": "in_stock",
            "price_usd": 0.0,
            "size_stock": {},
            "full_matrix": None,
            "elapsed_ms": elapsed_ms,
            "error": f"Unable to extract product JSON-LD or pricing from rendered page: {page_title}"
        }

    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
        return {
            "status": "error",
            "availability": "in_stock",
            "price_usd": 0.0,
            "elapsed_ms": elapsed_ms,
            "error": str(exc)
        }
