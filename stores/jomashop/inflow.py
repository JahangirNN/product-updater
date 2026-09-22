"""
Store Inflow Normalizer & Harvester: Jomashop (Luxury & Designer Watches)
Harvests 5 target watch collections (Versace, Tissot, Seiko, Citizen $100-$500, Michael Kors)
via Apollo GraphQL, normalizes attributes to canonical product dictionaries with
whole-rupee INR pricing, case diameter sizing options, and rich technical specs accordions.
Pure functional composition, zero classes (ADR 0004, ADR 0005, ADR 0006, ADR 0015, ADR 0018).
"""
import os
import sys
import json
import time
import re
import hashlib
import copy
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import httpx
try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

from storage.forex import get_usd_to_inr_rate
from storage.db import save_product, build_and_save_index, generate_product_id

GRAPHQL_URL = "https://www.jomashop.com/graphql"
CATEGORY_ID = "871"  # Watches

WHITELIST_BRANDS = ["Versace", "Tissot", "Seiko", "Citizen", "Michael Kors", "Ferragamo", "Movado"]

REJECTION_PATTERNS = [
    r"\bsunglasses\b", r"\beyewear\b", r"\bframes\b", r"\bshades\b",
    r"\bfragrance\b", r"\bperfume\b", r"\bcologne\b", r"\beau de parfum\b", r"\beau de toilette\b",
    r"\bjacket\b", r"\bcoat\b", r"\bshirt\b", r"\bdress\b", r"\bclothing\b", r"\bapparel\b", r"\bpants\b",
    r"\bhandbag\b", r"\btote\b", r"\bcrossbody\b", r"\bshoulder bag\b",
    r"\bearrings\b", r"\bnecklace\b", r"\bring\b", r"\bwriting instrument\b",
    r"\bwatch winder\b", r"\bstrap only\b", r"\bband only\b"
]

TARGET_COLLECTIONS = [
    {
        "brand": "Versace",
        "url": "https://www.jomashop.com/filters/watches?manufacturer=Versace&series=Chrono%7CChrono+Master%7CGreca+Fortuna%7CGreca+Jewel%7CSport+Chrono%7CV-Chrono%7CV-Contempo%7CHellenyium%7CGreca+Flourish%7CGreek%7CGreca+Sphere",
        "series": [
            "Chrono", "Chrono Master", "Greca Fortuna", "Greca Jewel", "Sport Chrono",
            "V-Chrono", "V-Contempo", "Hellenyium", "Greca Flourish", "Greek", "Greca Sphere"
        ],
        "price": None,
        "expected_count": 46
    },
    {
        "brand": "Tissot",
        "url": "https://www.jomashop.com/filters/watches?manufacturer=Tissot&series=Prx%7CSeastar%7CSeastar+1000%7CSeastar+1001%7CSeastar+2000%7CPr516%7CCarson%7CLe+Locle%7CPowermatic+80%7CT-Classic%7CChemin+Des+Tourelles%7CCarson+Premium%7CLady+Heart",
        "series": [
            "Prx", "Seastar", "Seastar 1000", "Seastar 1001", "Seastar 2000", "Pr516",
            "Carson", "Le Locle", "Powermatic 80", "T-Classic", "Chemin Des Tourelles",
            "Carson Premium", "Lady Heart"
        ],
        "price": None,
        "expected_count": 157
    },
    {
        "brand": "Seiko",
        "url": "https://www.jomashop.com/filters/watches?manufacturer=Seiko&series=5+Sports%7CChronograph%7CEssentials%7CPresage%7CProspex%7CProspex+Sea%7CQuartz%7CSport",
        "series": [
            "5 Sports", "Chronograph", "Essentials", "Presage", "Prospex",
            "Prospex Sea", "Quartz", "Sport"
        ],
        "price": None,
        "expected_count": 67
    },
    {
        "brand": "Citizen",
        "url": "https://www.jomashop.com/filters/watches?manufacturer=Citizen&price=%7B%22from%22%3A100%2C%22to%22%3A500%7D&series=Promaster+Dive%7CPromaster+Diver%7CPromaster+Navihawk%7CPromaster+Sky+Navihawk%7CPromaster+Sea%7CSports%7CSport+Luxury%7CSport+Automatic%7CPromaster+Marine%7CPromaster+Skyhawk%7CTsuyosa%7CPromaster+Dive+Automatic%7CPromaster+Skyhawk+U830",
        "series": [
            "Promaster Dive", "Promaster Diver", "Promaster Navihawk", "Promaster Sky Navihawk",
            "Promaster Sea", "Sports", "Sport Luxury", "Sport Automatic", "Promaster Marine",
            "Promaster Skyhawk", "Tsuyosa", "Promaster Dive Automatic", "Promaster Skyhawk U830"
        ],
        "price": {"from": "100", "to": "500"},
        "expected_count": 119
    },
    {
        "brand": "Michael Kors",
        "url": "https://www.jomashop.com/filters/watches?manufacturer=Michael+Kors&series=Lexington%7CBillie%7CPetite+Lexington%7CRunway%7CSlim+Runway%7CBradshaw%7CParker%7CCorey",
        "series": [
            "Lexington", "Billie", "Petite Lexington", "Runway", "Slim Runway",
            "Bradshaw", "Parker", "Corey"
        ],
        "price": None,
        "expected_count": 67
    },
    {
        "brand": "Ferragamo",
        "url": "https://www.jomashop.com/filters/watches?manufacturer=Ferragamo&gender=Unisex%7CWomens",
        "gender": ["Unisex", "Womens"],
        "series": None,
        "price": None,
        "expected_count": 15
    },
    {
        "brand": "Movado",
        "url": "https://www.jomashop.com/filters/watches?manufacturer=Movado&series=Bold%7CBold+Fusion%7CMuseum+Classic%7CMuseum%7CMusem%7CSeries+800%7CSe%7CBold+Quest%7CBold+Trend%7CSport&sort=price_asc%7CASC",
        "series": [
            "Bold", "Bold Fusion", "Museum Classic", "Museum", "Musem",
            "Series 800", "Se", "Bold Quest", "Bold Trend", "Sport"
        ],
        "gender": None,
        "price": None,
        "expected_count": 102
    }
]

PLP_QUERY_FILE = os.path.join(os.path.dirname(__file__), "plp.graphql")
with open(PLP_QUERY_FILE, "r", encoding="utf-8") as f:
    PLP_QUERY = f.read()

PDP_QUERY_FILE = os.path.join(os.path.dirname(__file__), "pdp.graphql")
with open(PDP_QUERY_FILE, "r", encoding="utf-8") as f:
    PDP_QUERY = f.read()



def is_valid_watch(raw_item: Dict[str, Any], brand: str, source_price: float) -> Tuple[bool, str]:
    """
    Strict boundary checks:
    1. Watches category only.
    2. Whitelisted brand only.
    3. Citizen price boundary ($100-$500).
    4. Reject non-watch items (sunglasses, fragrances, apparel, handbags, jewelry, etc.).
    """
    # Whitelist brand check
    if brand not in WHITELIST_BRANDS:
        return False, f"Brand '{brand}' not in whitelisted watch brands"

    # Citizen price boundary check
    if brand == "Citizen":
        if source_price < 100.0 or source_price > 500.0:
            return False, f"Citizen price ${source_price} violates [$100.00, $500.00] boundary"

    # Blacklist check
    name_lower = str(raw_item.get("name", "")).lower()
    url_key_lower = str(raw_item.get("url_key", "")).lower()
    text = f"{name_lower} {url_key_lower}"

    for pat in REJECTION_PATTERNS:
        if re.search(pat, text):
            # If the item contains "watch", do not reject unless it's genuinely non-watch
            if "watch" not in text or any(k in pat for k in ["sunglasses", "fragrance", "perfume", "jacket", "strap only", "watch winder"]):
                return False, f"Matched rejection pattern: '{pat}'"

    return True, "Valid"


def clean_case_diameter(raw_val: Optional[str], title: str = "", desc: str = "") -> str:
    """Normalize Case Diameter to standard 'XX mm' format."""
    if raw_val:
        m = re.search(r'(\d+(?:\.\d+)?)\s*mm', str(raw_val), re.IGNORECASE)
        if m:
            val = m.group(1)
            # Remove trailing .0 if integer
            if val.endswith(".0"):
                val = val[:-2]
            return f"{val} mm"

    # Fallback to title
    m = re.search(r'(\d+(?:\.\d+)?)\s*mm', title, re.IGNORECASE)
    if m:
        val = m.group(1)
        if val.endswith(".0"):
            val = val[:-2]
        return f"{val} mm"

    # Fallback to desc
    m = re.search(r'case\s*(?:size|diameter)[:\s]*(\d+(?:\.\d+)?)\s*mm', desc, re.IGNORECASE)
    if m:
        val = m.group(1)
        if val.endswith(".0"):
            val = val[:-2]
        return f"{val} mm"

    return "40 mm"


def clean_gender(raw_val: Optional[str], title: str = "") -> str:
    """Normalize Gender attribute with strict word boundaries."""
    text = (str(raw_val or "") + " " + title).lower()
    if re.search(r"\b(women|womens|women\'s|ladies|lady)\b", text, re.IGNORECASE):
        return "Women's"
    if re.search(r"\bunisex\b", text, re.IGNORECASE):
        return "Unisex"
    if re.search(r"\b(men|mens|men\'s)\b", text, re.IGNORECASE):
        return "Men's"
    return "Men's"


def generate_specs_accordion_html(specs: Dict[str, Any], overview_html: str, case_diameter: str) -> str:
    """
    Assemble descriptionHtml containing:
    1. Product overview
    2. Technical specifications table (<div class="product-specifications">)
    3. Interactive size guide accordion (<details class="size-guide-accordion">)
    """
    clean_overview = overview_html.strip() if overview_html else ""
    if not clean_overview:
        clean_overview = f"<p>Authentic {specs.get('Brand', 'luxury')} {specs.get('Series', '')} watch with {specs.get('Movement', 'precision')} movement and {case_diameter} case diameter.</p>"

    # Build specs table rows
    ordered_keys = [
        "Brand", "Series", "Model", "Gender", "Movement", "Engine", "Power Reserve",
        "Case Size", "Case Thickness", "Case Material", "Case Shape", "Case Back",
        "Dial Type", "Dial Color", "Crystal", "Hands", "Dial Markers", "Bezel",
        "Crown", "Band Type", "Band Material", "Band Color", "Band Width", "Clasp",
        "Water Resistance", "Calendar", "Functions", "Features", "Warranty", "UPC Code"
    ]

    rows_html = []
    for k in ordered_keys:
        v = specs.get(k)
        if v:
            rows_html.append(
                f'<tr style="border-bottom: 1px solid #eee;">'
                f'<td style="padding: 6px 12px; font-weight: 600; width: 35%; color: #555;">{k}</td>'
                f'<td style="padding: 6px 12px; color: #222;">{v}</td>'
                f'</tr>'
            )

    # Any remaining specs not in ordered list
    for k, v in specs.items():
        if k not in ordered_keys and v:
            rows_html.append(
                f'<tr style="border-bottom: 1px solid #eee;">'
                f'<td style="padding: 6px 12px; font-weight: 600; width: 35%; color: #555;">{k}</td>'
                f'<td style="padding: 6px 12px; color: #222;">{v}</td>'
                f'</tr>'
            )

    specs_table_html = (
        '<div class="product-specifications" style="margin: 20px 0;">\n'
        '  <h3 style="font-size: 16px; margin-bottom: 10px; font-weight: 600;">Technical Specifications</h3>\n'
        '  <table style="width: 100%; border-collapse: collapse; font-size: 13px;">\n'
        '    <tbody>\n'
        + "\n".join("      " + r for r in rows_html) +
        '\n    </tbody>\n'
        '  </table>\n'
        '</div>'
    )

    size_guide_accordion = (
        '<details class="size-guide-accordion" style="margin: 20px 0; padding: 12px; border: 1px solid #e0e0e0; border-radius: 6px;">\n'
        '  <summary style="font-weight: 600; cursor: pointer; font-size: 15px;">📏 Watch Sizing &amp; Case Dimension Guide</summary>\n'
        '  <div style="margin-top: 12px;">\n'
        '    <p style="font-size: 13px; color: #666; margin-bottom: 8px;">Standard wrist circumference &amp; case diameter matching guide:</p>\n'
        '    <table style="width: 100%; border-collapse: collapse; font-size: 13px;">\n'
        '      <thead>\n'
        '        <tr style="background-color: #f5f5f5;">\n'
        '          <th style="padding:6px 12px;text-align:center;">Case Diameter</th>\n'
        '          <th style="padding:6px 12px;text-align:center;">Recommended Wrist Size (Inches)</th>\n'
        '          <th style="padding:6px 12px;text-align:center;">Recommended Wrist Size (CM)</th>\n'
        '          <th style="padding:6px 12px;text-align:center;">Fit Style</th>\n'
        '        </tr>\n'
        '      </thead>\n'
        '      <tbody>\n'
        '        <tr><td style="padding:6px 12px;text-align:center;">28 mm – 34 mm</td><td style="padding:6px 12px;text-align:center;">5.0" – 6.0"</td><td style="padding:6px 12px;text-align:center;">12.5 – 15.0 cm</td><td style="padding:6px 12px;text-align:center;">Petite / Delicate</td></tr>\n'
        '        <tr><td style="padding:6px 12px;text-align:center;">36 mm – 38 mm</td><td style="padding:6px 12px;text-align:center;">6.0" – 6.75"</td><td style="padding:6px 12px;text-align:center;">15.0 – 17.0 cm</td><td style="padding:6px 12px;text-align:center;">Classic / Vintage Dress</td></tr>\n'
        '        <tr><td style="padding:6px 12px;text-align:center;">40 mm – 42 mm</td><td style="padding:6px 12px;text-align:center;">6.75" – 7.5"</td><td style="padding:6px 12px;text-align:center;">17.0 – 19.0 cm</td><td style="padding:6px 12px;text-align:center;">Contemporary Standard</td></tr>\n'
        '        <tr><td style="padding:6px 12px;text-align:center;">43 mm – 46 mm</td><td style="padding:6px 12px;text-align:center;">7.5" – 8.5"</td><td style="padding:6px 12px;text-align:center;">19.0 – 21.5 cm</td><td style="padding:6px 12px;text-align:center;">Sport / Bold Diver</td></tr>\n'
        '      </tbody>\n'
        '    </table>\n'
        '  </div>\n'
        '</details>'
    )

    return f"<div>{clean_overview}</div>\n{specs_table_html}\n{size_guide_accordion}"


def post_graphql(query: str, variables: Dict[str, Any], operation_name: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
    """Execute GraphQL query with retry and fallback."""
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    }
    payload = {
        "operationName": operation_name,
        "query": query,
        "variables": variables
    }

    for attempt in range(max_retries):
        try:
            if HAS_CURL_CFFI:
                resp = cffi_requests.post(
                    GRAPHQL_URL,
                    json=payload,
                    headers=headers,
                    impersonate="chrome124",
                    timeout=20
                )
            else:
                with httpx.Client(timeout=20.0) as client:
                    resp = client.post(GRAPHQL_URL, json=payload, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                if "errors" not in data:
                    return data
                print(f"  [ERROR:GQL] {operation_name} returned errors: {data.get('errors')}")
            elif resp.status_code == 429:
                time.sleep(2.0 * (2 ** attempt))
                continue
        except Exception:
            time.sleep(0.5 * (2 ** attempt))

    return None


def harvest_plp_for_collection(collection_cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Harvest all product stubs for a single brand collection via PLP query."""
    brand = collection_cfg["brand"]
    series_list = collection_cfg.get("series")
    gender_list = collection_cfg.get("gender")
    price_cfg = collection_cfg.get("price")

    filter_obj = {
        "category_id": {"eq": CATEGORY_ID},
        "manufacturer": {"eq": brand}
    }
    if series_list:
        filter_obj["series"] = {"in": series_list}
    if gender_list:
        filter_obj["gender"] = {"in": gender_list}
    if price_cfg:
        filter_obj["price"] = price_cfg

    items = []
    page = 1
    page_size = 100

    while True:
        variables = {
            "id": CATEGORY_ID,
            "pageSize": page_size,
            "currentPage": page,
            "onServer": False,
            "filter": filter_obj
        }
        res = post_graphql(PLP_QUERY, variables, "category")
        if not res:
            break

        prods_data = res.get("data", {}).get("products", {})
        page_items = prods_data.get("items", [])
        items.extend(page_items)

        total_pages = prods_data.get("page_info", {}).get("total_pages", 1)
        if page >= total_pages or not page_items:
            break
        page += 1

    return items


def fetch_pdp_for_url_key(url_key: str) -> Optional[Dict[str, Any]]:
    """Fetch full PDP details for an individual product via GraphQL."""
    variables = {
        "urlKey": url_key,
        "onServer": False
    }
    res = post_graphql(PDP_QUERY, variables, "productDetail")
    if not res:
        return None

    items = res.get("data", {}).get("productDetail", {}).get("items", [])
    if items:
        return items[0]
    return None


def harvest_catalog(filter_urls: Optional[List[str]] = None, max_workers: int = 4) -> List[Dict[str, Any]]:
    """
    Harvest 100% of products across target collections:
    Phase 1: Fast PLP category queries (pageSize=100)
    Phase 2: Concurrent PDP enrichment with rate-safe workers
    """
    print(f"[*] Starting Jomashop catalog harvest across {len(TARGET_COLLECTIONS)} target collections...")

    all_plp_items = []
    for cfg in TARGET_COLLECTIONS:
        brand = cfg["brand"]
        print(f"  -> Harvesting PLP for {brand}...")
        c_items = harvest_plp_for_collection(cfg)
        print(f"     Found {len(c_items)} products for {brand} (expected: {cfg['expected_count']})")
        for it in c_items:
            it["_target_brand"] = brand
            it["_target_collection"] = cfg
        all_plp_items.extend(c_items)

    print(f"[*] Total PLP products harvested: {len(all_plp_items)}. Enriching with PDP specifications...")

    enriched_products = []
    # Fetch PDP details with ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_item = {
            executor.submit(fetch_pdp_for_url_key, it["url_key"]): it
            for it in all_plp_items
        }
        done_count = 0
        total = len(all_plp_items)

        for future in as_completed(future_to_item):
            plp_it = future_to_item[future]
            try:
                pdp_data = future.result()
            except Exception as e:
                pdp_data = None

            enriched_products.append({
                "plp": plp_it,
                "pdp": pdp_data,
                "brand": plp_it.get("_target_brand")
            })

            done_count += 1
            if done_count % 50 == 0 or done_count == total:
                print(f"     Enriched {done_count}/{total} products...")

    return enriched_products


def parse_pdp(raw_product_bundle: Dict[str, Any], forex_rate: float) -> Optional[Dict[str, Any]]:
    """
    Transform raw PLP + PDP payload into canonical Jomashop product dictionary.
    Enforces whole-rupee INR math (0 fractional paise), Case Diameter variant sizing,
    and structured technical specifications accordion.
    """
    plp_it = raw_product_bundle.get("plp", {})
    pdp_it = raw_product_bundle.get("pdp") or {}
    brand = raw_product_bundle.get("brand") or pdp_it.get("manufacturer") or "Jomashop"

    # 1. Price extraction & validation
    p_info = pdp_it.get("price_range", {}).get("minimum_price") or plp_it.get("price_range", {}).get("minimum_price") or {}
    final_p = p_info.get("final_price", {}).get("value")
    regular_p = p_info.get("regular_price", {}).get("value")
    msrp_p = p_info.get("msrp_price", {}).get("value") or pdp_it.get("msrp") or plp_it.get("msrp")

    source_price = float(final_p or regular_p or 0.0)
    if source_price <= 0.0:
        return None

    compare_val = msrp_p or regular_p
    source_compare_price = float(compare_val) if compare_val and float(compare_val) > source_price else None

    # Strict boundary check
    valid, reason = is_valid_watch(plp_it, brand, source_price)
    if not valid:
        print(f"  [REJECTED] {plp_it.get('name')}: {reason}")
        return None

    # 2. Identity & Naming
    title = str(pdp_it.get("name") or plp_it.get("name") or "").strip()
    raw_sku = str(pdp_it.get("sku") or plp_it.get("sku") or "").strip()
    clean_sku = raw_sku
    url_key = str(pdp_it.get("url_key") or plp_it.get("url_key") or "").strip()
    source_url = f"https://www.jomashop.com/{url_key}.html"

    # 3. Technical Specifications Extraction
    specs = {}
    more_groups = pdp_it.get("moredetails", {}).get("more_details", [])
    for g in more_groups:
        for attr in g.get("group_attributes", []):
            lbl = attr.get("attribute_label")
            val = attr.get("attribute_value")
            if lbl and val:
                specs[lbl] = val.strip()

    # Ensure baseline specs are populated
    if "Brand" not in specs:
        specs["Brand"] = brand
    series = specs.get("Series") or specs.get("Collection Name") or "Classic"
    if "Series" not in specs:
        specs["Series"] = series

    model_id = pdp_it.get("model_id") or specs.get("Model")
    if model_id and "Model" not in specs:
        specs["Model"] = model_id

    # 4. Gender & Sizing
    gender = clean_gender(specs.get("Gender") or pdp_it.get("moredetails", {}).get("gender_label"), title)
    specs["Gender"] = gender

    raw_case_diam = specs.get("Case Diameter") or specs.get("Case Size")
    case_diameter = clean_case_diameter(raw_case_diam, title=title, desc=pdp_it.get("description", {}).get("html", ""))
    specs["Case Size"] = case_diameter

    # 5. Whole-Rupee INR Math (ADR 0006)
    price_inr = float(round(source_price * forex_rate))
    compare_inr = float(round(source_compare_price * forex_rate)) if source_compare_price else None

    # 6. High-Res Media Gallery (cdn2.jomashop.com master uncompressed)
    images = []
    # Primary image from pdp
    pdp_img = pdp_it.get("image", {}).get("url_nocache")
    if pdp_img and pdp_img.startswith("http") and pdp_img not in images:
        images.append(pdp_img)

    for mg in pdp_it.get("media_gallery", []):
        img_url = mg.get("url_nocache")
        if img_url and img_url.startswith("http") and img_url not in images:
            images.append(img_url)

    # Fallback to plp images if needed
    if not images:
        for mg in plp_it.get("media_gallery", []):
            for sz in mg.get("sizes", []):
                u = sz.get("url")
                if u and u.startswith("http") and u not in images:
                    images.append(u)

    if not images:
        images.append(f"https://cdn2.jomashop.com/media/catalog/product/placeholder_{clean_sku}.jpg")

    hero_image = images[0]

    # 7. Stock & Availability
    stock_status = str(pdp_it.get("stock_status") or plp_it.get("stock_status") or "IN_STOCK").upper()
    is_in_stock = (stock_status == "IN_STOCK")
    availability = "in_stock" if is_in_stock else "out_of_stock"

    # 8. Single Variant with Case Diameter Sizing Option
    dial_color = specs.get("Dial Color") or "Dial"
    band_info = specs.get("Band Material") or specs.get("Band Type") or "Strap"
    variant_title = f"{case_diameter} - {dial_color} / {band_info}"

    variants = [
        {
            "id": None,
            "sku": clean_sku,
            "title": variant_title,
            "price": f"{price_inr:.2f}",
            "price_current": price_inr,
            "compare_at_price": f"{compare_inr:.2f}" if compare_inr else None,
            "source_price": source_price,
            "source_compare_at_price": source_compare_price,
            "currency": "INR",
            "source_currency": "USD",
            "in_stock": is_in_stock,
            "image_url": hero_image,
            "option_values": [
                {
                    "option_name": "Case Diameter",
                    "name": case_diameter
                }
            ]
        }
    ]

    product_options = [
        {
            "name": "Case Diameter",
            "values": [
                {
                    "name": case_diameter
                }
            ]
        }
    ]

    # 9. Rich descriptionHtml with Technical Specs Table & Size Guide Accordion
    raw_desc = pdp_it.get("description", {}).get("html", "")
    description_html = generate_specs_accordion_html(specs, raw_desc, case_diameter)

    # 10. Taxonomy & Groups (Footwear Audit Isolation Invariant)
    brand_slug = brand.lower().replace(" ", "")
    series_slug = re.sub(r'[^a-zA-Z0-9]+', '-', series.lower()).strip('-') if series else "general"

    # Groups MUST NEVER contain footwear or apparel keywords!
    groups = [
        "watches",
        brand_slug,
        f"{brand_slug}-{series_slug}"
    ]

    tags = [
        "Watches",
        brand,
        series,
        gender,
        "Jomashop"
    ]
    movement = specs.get("Movement")
    if movement:
        tags.append(movement)

    # 11. Deterministic Primary Key
    product_id = generate_product_id("jomashop", clean_sku)
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    material = specs.get("Case Material") or specs.get("Band Material") or "Stainless Steel"

    return {
        "id": product_id,
        "source_store": "jomashop",
        "source_url": source_url,
        "handle": url_key,
        "title": title,
        "vendor": brand,
        "product_type": "Watches",
        "gender": gender,
        "source_sku": clean_sku,
        "source_price": source_price,
        "source_compare_at_price": source_compare_price,
        "current_price": price_inr,
        "compare_at_price": compare_inr,
        "currency": "INR",
        "source_currency": "USD",
        "forex_rate_used": forex_rate,
        "availability": availability,
        "is_active": is_in_stock,
        "material": material,
        "specifications": specs,
        "descriptionHtml": description_html,
        "images": images,
        "variants": variants,
        "product_options": product_options,
        "tags": list(dict.fromkeys(tags)),
        "groups": sorted(list(set(groups))),
        "created_at": now_iso,
        "updated_at": now_iso,
        "last_verified_at": now_iso,
        "shopify_sync_pending": False
    }


def persist_catalog(products: List[Dict[str, Any]], base_dir: str = "storage/db") -> Tuple[int, int]:
    """Persist all canonical products atomically and update master index.json."""
    persisted = 0
    total = len(products)
    print(f"[*] Persisting {total} Jomashop products to {base_dir}/jomashop/products/...")

    for p in products:
        if p and isinstance(p, dict):
            save_product(p, base_dir=base_dir)
            persisted += 1

    print(f"[*] Successfully saved {persisted}/{total} product files. Updating master index.json...")
    build_and_save_index(base_dir=base_dir)
    print("[*] Master index.json updated successfully.")
    return persisted, total


def run_ingestion(base_dir: str = "storage/db") -> Dict[str, Any]:
    """Execute end-to-end ingestion pipeline for Jomashop."""
    print("=" * 70)
    print("JOMASHOP X-MODE INGESTION PIPELINE")
    print("=" * 70)

    # 1. Forex Rate
    forex_rate = get_usd_to_inr_rate()
    print(f"[*] Active USD to INR Forex Rate: {forex_rate:.4f}")

    # 2. Harvest Catalog
    raw_products = harvest_catalog(max_workers=4)
    print(f"[*] Total raw products fetched: {len(raw_products)}")

    # 3. Canonical Normalization
    canonical_products = []
    brand_counts = {}

    for rp in raw_products:
        p = parse_pdp(rp, forex_rate)
        if p:
            canonical_products.append(p)
            v = p.get("vendor", "Unknown")
            brand_counts[v] = brand_counts.get(v, 0) + 1

    print(f"[*] Normalized {len(canonical_products)} canonical watch records:")
    for b, c in sorted(brand_counts.items()):
        print(f"    - {b:15}: {c:3} products")

    # 4. Atomic Persistence & Index Update
    persisted, total = persist_catalog(canonical_products, base_dir=base_dir)

    summary = {
        "status": "success",
        "total_harvested": len(raw_products),
        "total_normalized": len(canonical_products),
        "persisted_count": persisted,
        "brand_counts": brand_counts,
        "forex_rate": forex_rate
    }
    return summary


if __name__ == "__main__":
    run_ingestion()
