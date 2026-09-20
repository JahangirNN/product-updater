"""
Store Inflow Normalizer: JD Sports (Nike Footwear Collections)
Transforms raw JD Sports search listings and PDP hydrated JSON-LD / RSC states
into canonical product dictionaries with multi-tier sizing classification.
Pure functions only, zero classes (ADR 0004, ADR 0005, ADR 0006, ADR 0015, ADR 0016).
"""
import os
import sys
import re
import time
import hashlib
import copy
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from storage.forex import get_usd_to_inr_rate

# ==============================================================================
# 1. Nike Official Size Conversion Tables (Adult, Youth/GS, Kids/PS, Toddler)
# ==============================================================================

NIKE_MEN_US_TO_UK = {
    "6": "5.5", "6.0": "5.5", "6.5": "6",
    "7": "6", "7.0": "6", "7.5": "6.5",
    "8": "7", "8.0": "7", "8.5": "7.5",
    "9": "8", "9.0": "8", "9.5": "8.5",
    "10": "9", "10.0": "9", "10.5": "9.5",
    "11": "10", "11.0": "10", "11.5": "10.5",
    "12": "11", "12.0": "11", "12.5": "11.5",
    "13": "12", "13.0": "12", "14": "13", "14.0": "13",
    "15": "14", "15.0": "14"
}

NIKE_MEN_US_TO_EU = {
    "6": "38.5", "6.0": "38.5", "6.5": "39",
    "7": "40", "7.0": "40", "7.5": "40.5",
    "8": "41", "8.0": "41", "8.5": "42",
    "9": "42.5", "9.0": "42.5", "9.5": "43",
    "10": "44", "10.0": "44", "10.5": "44.5",
    "11": "45", "11.0": "45", "11.5": "45.5",
    "12": "46", "12.0": "46", "12.5": "47",
    "13": "47.5", "13.0": "47.5", "14": "48.5", "14.0": "48.5",
    "15": "49.5", "15.0": "49.5"
}

NIKE_WOMEN_US_TO_UK = {
    "5": "2.5", "5.0": "2.5", "5.5": "3",
    "6": "3.5", "6.0": "3.5", "6.5": "4",
    "7": "4.5", "7.0": "4.5", "7.5": "5",
    "8": "5.5", "8.0": "5.5", "8.5": "6",
    "9": "6.5", "9.0": "6.5", "9.5": "7",
    "10": "7.5", "10.0": "7.5", "10.5": "8",
    "11": "8.5", "11.0": "8.5", "11.5": "9",
    "12": "9.5", "12.0": "9.5"
}

NIKE_WOMEN_US_TO_EU = {
    "5": "35.5", "5.0": "35.5", "5.5": "36",
    "6": "36.5", "6.0": "36.5", "6.5": "37.5",
    "7": "38", "7.0": "38", "7.5": "38.5",
    "8": "39", "8.0": "39", "8.5": "40",
    "9": "40.5", "9.0": "40.5", "9.5": "41",
    "10": "42", "10.0": "42", "10.5": "42.5",
    "11": "43", "11.0": "43", "11.5": "44",
    "12": "44.5", "12.0": "44.5"
}

NIKE_GS_US_TO_UK = {
    "3.5": "3", "4": "3.5", "4.0": "3.5", "4.5": "4",
    "5": "4.5", "5.0": "4.5", "5.5": "5",
    "6": "5.5", "6.0": "5.5", "6.5": "6",
    "7": "6", "7.0": "6"
}

NIKE_GS_US_TO_EU = {
    "3.5": "35.5", "4": "36", "4.0": "36", "4.5": "36.5",
    "5": "37.5", "5.0": "37.5", "5.5": "38",
    "6": "38.5", "6.0": "38.5", "6.5": "39",
    "7": "40", "7.0": "40"
}

NIKE_PS_US_TO_UK = {
    "10.5": "10", "11": "10.5", "11.0": "10.5", "11.5": "11",
    "12": "11.5", "12.0": "11.5", "12.5": "12",
    "13": "12.5", "13.0": "12.5", "13.5": "13",
    "1": "13.5", "1.0": "13.5", "1.5": "1",
    "2": "1.5", "2.0": "1.5", "2.5": "2",
    "3": "2.5", "3.0": "2.5"
}

NIKE_PS_US_TO_EU = {
    "10.5": "27.5", "11": "28", "11.0": "28", "11.5": "28.5",
    "12": "29.5", "12.0": "29.5", "12.5": "30",
    "13": "31", "13.0": "31", "13.5": "31.5",
    "1": "32", "1.0": "32", "1.5": "33",
    "2": "33.5", "2.0": "33.5", "2.5": "34",
    "3": "35", "3.0": "35"
}

NIKE_TD_US_TO_UK = {
    "1": "0.5", "1.0": "0.5",
    "2": "1.5", "2.0": "1.5",
    "3": "2.5", "3.0": "2.5",
    "4": "3.5", "4.0": "3.5",
    "5": "4.5", "5.0": "4.5",
    "6": "5.5", "6.0": "5.5",
    "7": "6.5", "7.0": "6.5",
    "8": "7.5", "8.0": "7.5",
    "9": "8.5", "9.0": "8.5",
    "10": "9.5", "10.0": "9.5"
}

NIKE_TD_US_TO_EU = {
    "1": "16", "1.0": "16",
    "2": "17", "2.0": "17",
    "3": "18.5", "3.0": "18.5",
    "4": "19.5", "4.0": "19.5",
    "5": "21", "5.0": "21",
    "6": "22", "6.0": "22",
    "7": "23.5", "7.0": "23.5",
    "8": "25", "8.0": "25",
    "9": "26", "9.0": "26",
    "10": "27", "10.0": "27"
}

def _lookup_chart(chart: Dict[str, str], val: float, fallback: str) -> str:
    k_g = f"{val:g}"
    k_f = f"{val:.1f}"
    return chart.get(k_g) or chart.get(k_f) or fallback


# ==============================================================================
# 2. Sizing Category Classification & Gender Parsing
# ==============================================================================

def classify_sizing_category(
    title: str,
    breadcrumbs: Optional[List[Any]] = None,
    raw_sizes: Optional[List[Any]] = None
) -> str:
    """
    Deterministic classification of footwear into age tier:
    - Adult (US >= 6.0 M / >= 5.0 W)
    - Grade School (Big Kids, US 3.5Y – 7.0Y)
    - Preschool (Little Kids, US 10.5C – 3.0Y)
    - Toddler (Infant, US 2C – 10C)
    """
    text = (title or "").lower()

    # 1. Breadcrumbs signal
    bc_text = ""
    if breadcrumbs:
        if isinstance(breadcrumbs, list):
            for b in breadcrumbs:
                if isinstance(b, dict):
                    bc_text += " " + str(b.get("name") or b.get("item", {}).get("name") or "").lower()
                elif isinstance(b, str):
                    bc_text += " " + b.lower()
        elif isinstance(breadcrumbs, str):
            bc_text = breadcrumbs.lower()

    combined = f"{text} {bc_text}"

    # Priority 1: Toddler / Infant (use word boundaries to avoid false positives like 'ltd')
    if re.search(r'\b(toddler|infant|baby|crib|boys-toddler|girls-toddler|td)\b', combined, re.IGNORECASE):
        if "big kid" not in combined:
            return "Toddler"

    # Priority 2: Preschool / Little Kids (use word boundaries to avoid 'straps')
    if re.search(r'\b(little kids|preschool|ps|boys-little-kids|girls-little-kids)\b', combined, re.IGNORECASE):
        return "Preschool"

    # Priority 3: Grade School / Big Kids (use word boundaries to avoid 'wings')
    if re.search(r'\b(big kids|grade school|gs|big boys|big girls|boys-big-kids|girls-big-kids)\b', combined, re.IGNORECASE):
        return "Grade School"

    # Priority 4: Raw sizes inspection
    if raw_sizes:
        size_strs = []
        for s in raw_sizes:
            if isinstance(s, dict):
                size_strs.append(str(s.get("size") or s.get("name") or ""))
            else:
                size_strs.append(str(s))
        has_c = any(bool(re.search(r'\b\d+(\.5)?\s*c\b', sz, re.IGNORECASE)) for sz in size_strs)
        has_y = any(bool(re.search(r'\b\d+(\.5)?\s*y\b', sz, re.IGNORECASE)) for sz in size_strs)
        if has_c and not has_y:
            return "Toddler"
        if has_c and has_y:
            return "Preschool"
        if has_y and not has_c:
            return "Grade School"

    # Default to Adult
    return "Adult"


def determine_gender(name: str, sizing_category: str = "Adult", model_gender: Optional[List[str]] = None) -> str:
    """Determine clean gender string (Men's, Women's, Boys', Girls', Kids', Unisex)."""
    name_lower = name.lower()
    if model_gender and isinstance(model_gender, list) and model_gender:
        mg = str(model_gender[0]).lower()
        if "women" in mg:
            return "Women's"
        if "men" in mg:
            return "Men's"
        if "girl" in mg:
            return "Girls'"
        if "boy" in mg:
            return "Boys'"

    if "women" in name_lower:
        return "Women's"
    elif "men" in name_lower and "women" not in name_lower:
        return "Men's"
    elif "girl" in name_lower:
        return "Girls'"
    elif "boy" in name_lower:
        return "Boys'"

    if sizing_category in ("Grade School", "Preschool", "Toddler"):
        return "Kids'"

    return "Unisex"


# ==============================================================================
# 3. Size Formatting & Conversions
# ==============================================================================

def parse_and_format_size(
    raw_size_str: str,
    sizing_category: str,
    gender: str = "Men's"
) -> Tuple[str, str, str, float]:
    """
    Parses raw JD Sports size string (e.g. '8.0', '7.0', '11.5', '10.5C', '3.5Y')
    and returns (size_label, uk_str, eu_str, numeric_val).
    Enforces C/Y token preservation to eliminate numeric collisions.
    - Toddler: US {size}C (e.g. US 7C)
    - Preschool: US {size}C (if >= 10) or US {size}Y (if < 10)
    - Grade School: US {size}Y (e.g. US 7.0Y)
    - Adult: US {size} (e.g. US 7.0)
    """
    s = str(raw_size_str).strip()
    m = re.search(r'(\d+(?:\.\d+)?)', s)
    if m:
        clean_num_str = m.group(1)
        val = float(clean_num_str)
    else:
        clean_num_str = "0"
        val = 0.0

    if sizing_category == "Toddler":
        # Format integer values without trailing .0 for C suffix: US 7C, US 10C (or 7.5C if half size)
        c_label = f"{val:g}" if val > 0 else clean_num_str
        size_label = f"US {c_label}C"
        uk_str = _lookup_chart(NIKE_TD_US_TO_UK, val, f"{max(0.0, val - 0.5):g}")
        eu_str = _lookup_chart(NIKE_TD_US_TO_EU, val, f"{15.0 + (val * 1.2):.1f}")
        return size_label, uk_str, eu_str, val

    elif sizing_category == "Preschool":
        if val >= 10.0:
            c_label = f"{val:g}" if val > 0 else clean_num_str
            size_label = f"US {c_label}C"
        else:
            y_label = f"{val:.1f}" if val > 0 else clean_num_str
            size_label = f"US {y_label}Y"
        uk_str = _lookup_chart(NIKE_PS_US_TO_UK, val, f"{max(0.0, val - 0.5):g}")
        eu_str = _lookup_chart(NIKE_PS_US_TO_EU, val, f"{27.0 + (val * 1.0):.1f}")
        return size_label, uk_str, eu_str, val

    elif sizing_category == "Grade School":
        # Format with .1f for Grade School sizes: US 7.0Y, US 3.5Y
        y_label = f"{val:.1f}" if val > 0 else clean_num_str
        size_label = f"US {y_label}Y"
        uk_str = _lookup_chart(NIKE_GS_US_TO_UK, val, f"{max(0.0, val - 0.5):g}")
        eu_str = _lookup_chart(NIKE_GS_US_TO_EU, val, f"{32.0 + (val * 1.25):.1f}")
        return size_label, uk_str, eu_str, val

    else:
        # Adult: US 7.0, US 8.5
        ad_label = f"{val:.1f}" if val > 0 else clean_num_str
        size_label = f"US {ad_label}"
        if "women" in gender.lower():
            uk_str = _lookup_chart(NIKE_WOMEN_US_TO_UK, val, f"{max(0.0, val - 2.5):g}")
            eu_str = _lookup_chart(NIKE_WOMEN_US_TO_EU, val, f"{30.5 + (val * 1.25):.1f}")
        else:
            uk_str = _lookup_chart(NIKE_MEN_US_TO_UK, val, f"{max(0.0, val - 1.0):g}")
            eu_str = _lookup_chart(NIKE_MEN_US_TO_EU, val, f"{32.5 + (val * 1.25):.1f}")
        return size_label, uk_str, eu_str, val


# ==============================================================================
# 4. Description HTML & Size Guide Accordion Generator (ADR 0006)
# ==============================================================================

def generate_description_html(
    title: str,
    desc_html: str,
    sizing_category: str,
    gender: str,
    specs: Dict[str, Any],
    sizes: List[Dict[str, Any]]
) -> str:
    """
    Generate rich HTML body with specifications table and Nike size guide accordion.
    """
    clean_desc = desc_html.strip() if desc_html else f"<p>{title} brings iconic Nike cushioning, heritage style, and everyday comfort.</p>"

    # Specifications Table
    specs_rows = "".join(
        f"<tr><td style='padding:6px 12px;font-weight:600;'>{k}</td><td style='padding:6px 12px;'>{v}</td></tr>"
        for k, v in specs.items()
        if v and not str(k).startswith("Available")
    )
    specs_html = f"""
<div class="product-specifications" style="margin: 20px 0;">
  <h3 style="font-size: 16px; margin-bottom: 8px;">Specifications</h3>
  <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
    <tbody>{specs_rows}</tbody>
  </table>
</div>
"""

    # Size Conversion Accordion Table (ADR 0006)
    size_rows = "".join(
        f"<tr><td style='padding:6px 12px;text-align:center;'>{s['size_label']}</td>"
        f"<td style='padding:6px 12px;text-align:center;'>UK {s['uk_str']}</td>"
        f"<td style='padding:6px 12px;text-align:center;'>EU {s['eu_str']}</td>"
        f"<td style='padding:6px 12px;text-align:center;'>{'In Stock' if s['in_stock'] else 'Out of Stock'}</td></tr>"
        for s in sizes
    )

    accordion_html = f"""
<details class="size-guide-accordion" style="margin: 20px 0; padding: 12px; border: 1px solid #e0e0e0; border-radius: 6px;">
  <summary style="font-weight: 600; cursor: pointer; font-size: 15px;">Nike Size Guide &amp; Conversions ({sizing_category} - {gender})</summary>
  <div style="margin-top: 12px;">
    <p style="font-size: 13px; color: #666; margin-bottom: 8px;">Official Nike footwear size conversion matrix (US / UK / EU):</p>
    <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
      <thead>
        <tr style="background-color: #f5f5f5;">
          <th style="padding:6px 12px;text-align:center;">US Size</th>
          <th style="padding:6px 12px;text-align:center;">UK Size</th>
          <th style="padding:6px 12px;text-align:center;">EU Size</th>
          <th style="padding:6px 12px;text-align:center;">Availability</th>
        </tr>
      </thead>
      <tbody>{size_rows}</tbody>
    </table>
  </div>
</details>
"""
    return f"<div class='product-description'>{clean_desc}</div>\n{specs_html}\n{accordion_html}"


# ==============================================================================
# 5. Pure Ingestion Parser (`parse_product_payload`)
# ==============================================================================

def parse_product_payload(
    raw_data: Dict[str, Any],
    usd_to_inr_rate: Optional[float] = None,
    group_name: str = "footwear"
) -> Optional[Dict[str, Any]]:
    """
    Pure functional parser transforming raw JD Sports payload into canonical product format.
    Accepts:
    1. PDP JSON-LD ProductGroup or Product object
    2. Search item representation
    3. Pre-extracted dictionary

    Enforces:
    - Multi-tier sizing classification (Adult, Grade School, Preschool, Toddler)
    - Size token preservation (US 7C, US 7.0Y vs US 7.0)
    - Colorway title suffixing ({model_name} - {color})
    - Whole-rupee INR math (round(source_price * forex_rate), 0 decimal paise)
    - Parent-variant stock harmony (ADR 0015)
    - Primary key: SHA256("jdsports::" + sku)[:16]
    """
    if not raw_data or not isinstance(raw_data, dict):
        return None

    if usd_to_inr_rate is None or usd_to_inr_rate <= 0:
        usd_to_inr_rate = get_usd_to_inr_rate()

    # 1. Detect Payload Shape & Basic Attributes
    ld_type = raw_data.get("@type", "")
    is_product_group = ld_type == "ProductGroup"
    is_single_product = ld_type == "Product"

    title_raw = str(raw_data.get("name") or raw_data.get("title") or "").strip()
    if not title_raw:
        return None

    breadcrumbs = raw_data.get("breadcrumbs") or raw_data.get("breadcrumb") or []
    raw_sizes_list = raw_data.get("sizes") or []

    sizing_category = classify_sizing_category(title_raw, breadcrumbs, raw_sizes_list)
    gender = determine_gender(title_raw, sizing_category, raw_data.get("genders"))

    # Determine Style/SKU & Product Group ID
    product_group_id = str(raw_data.get("productGroupID") or raw_data.get("product_group_id") or "").strip()
    sku = str(raw_data.get("sku") or raw_data.get("styleCode") or raw_data.get("source_sku") or "").strip()
    color = str(raw_data.get("color") or raw_data.get("colorName") or "").strip()

    # 2. Extract Variants & Sizing Matrix
    raw_variants = []
    if is_product_group and "hasVariant" in raw_data:
        raw_variants = raw_data["hasVariant"]
    elif "variants" in raw_data and isinstance(raw_data["variants"], list):
        raw_variants = raw_data["variants"]
    elif is_single_product:
        raw_variants = [raw_data]

    source_price = 0.0
    source_compare_price = None

    parsed_sizes = []
    discovered_images = []

    # Check top-level offers
    top_offers = raw_data.get("offers") or {}
    if isinstance(top_offers, list) and top_offers:
        top_offers = top_offers[0]
    if isinstance(top_offers, dict):
        try:
            source_price = float(top_offers.get("price") or 0.0)
        except (ValueError, TypeError):
            source_price = 0.0

    if not source_price:
        try:
            source_price = float(raw_data.get("source_price") or raw_data.get("price") or 0.0)
        except (ValueError, TypeError):
            source_price = 0.0

    if raw_data.get("source_compare_at_price"):
        try:
            source_compare_price = float(raw_data["source_compare_at_price"])
        except (ValueError, TypeError):
            source_compare_price = None

    # Parse variants array
    for v in raw_variants:
        if not isinstance(v, dict):
            continue
        v_sku = str(v.get("sku") or "").strip()
        v_size_raw = str(v.get("size") or v.get("title") or v.get("name") or "").strip()
        if not v_size_raw:
            continue

        # Extract price
        v_offers = v.get("offers") or {}
        if isinstance(v_offers, list) and v_offers:
            v_offers = v_offers[0]
        v_price = source_price
        v_in_stock = False
        if isinstance(v_offers, dict):
            try:
                p_val = float(v_offers.get("price") or 0.0)
                if p_val > 0:
                    v_price = p_val
            except (ValueError, TypeError):
                pass
            avail_str = str(v_offers.get("availability") or "").lower()
            v_in_stock = ("instock" in avail_str or "in_stock" in avail_str)
        else:
            v_in_stock = bool(v.get("in_stock", False) or v.get("available", False))

        if not sku and v_sku:
            sku = v_sku
        if not color and v.get("color"):
            color = str(v.get("color")).strip()

        v_img = v.get("image") or v.get("image_url")
        if v_img and isinstance(v_img, str) and v_img.startswith("http"):
            if v_img not in discovered_images:
                discovered_images.append(v_img)

        label, uk, eu, num_val = parse_and_format_size(v_size_raw, sizing_category, gender)
        parsed_sizes.append({
            "size_label": label,
            "raw_size": v_size_raw,
            "numeric_size": num_val,
            "uk_str": uk,
            "eu_str": eu,
            "in_stock": v_in_stock,
            "price_usd": v_price if v_price > 0 else source_price,
            "sku": v_sku
        })

    # If no variants were extracted from raw_variants, check raw_sizes_list
    if not parsed_sizes and raw_sizes_list:
        for s_item in raw_sizes_list:
            if isinstance(s_item, dict):
                s_name = str(s_item.get("size") or s_item.get("name") or "").strip()
                s_stock = bool(s_item.get("in_stock", False) or s_item.get("active", False))
                s_sku = str(s_item.get("sku") or "").strip()
            else:
                s_name = str(s_item).strip()
                s_stock = True
                s_sku = ""

            if not s_name:
                continue

            label, uk, eu, num_val = parse_and_format_size(s_name, sizing_category, gender)
            parsed_sizes.append({
                "size_label": label,
                "raw_size": s_name,
                "numeric_size": num_val,
                "uk_str": uk,
                "eu_str": eu,
                "in_stock": s_stock,
                "price_usd": source_price,
                "sku": s_sku
            })

    # If still no sizes, create standard placeholder if valid footwear
    if not parsed_sizes:
        label, uk, eu, num_val = parse_and_format_size("Standard", sizing_category, gender)
        parsed_sizes.append({
            "size_label": "One Size",
            "raw_size": "One Size",
            "numeric_size": 0.0,
            "uk_str": "Standard",
            "eu_str": "Standard",
            "in_stock": True,
            "price_usd": source_price,
            "sku": sku
        })

    # Deduplicate sizes by size_label (merging stock)
    size_map: Dict[str, Dict[str, Any]] = {}
    for s in parsed_sizes:
        lbl = s["size_label"]
        if lbl not in size_map:
            size_map[lbl] = s
        else:
            if s["in_stock"]:
                size_map[lbl]["in_stock"] = True
            if not size_map[lbl]["sku"] and s["sku"]:
                size_map[lbl]["sku"] = s["sku"]

    def _size_sort_key(item: Dict[str, Any]) -> float:
        num = item.get("numeric_size", 0.0)
        lbl = item.get("size_label", "")
        if sizing_category == "Preschool" and "Y" in lbl:
            return num + 13.5
        return num

    deduped_sizes = list(size_map.values())
    deduped_sizes.sort(key=_size_sort_key)

    if not sku:
        sku = product_group_id or hashlib.sha256(title_raw.encode("utf-8")).hexdigest()[:10]

    # Collect images
    images = []
    if "images" in raw_data and isinstance(raw_data["images"], list):
        for img in raw_data["images"]:
            if isinstance(img, str) and img.startswith("http") and img not in images:
                images.append(img)
            elif isinstance(img, dict) and img.get("url") and img["url"] not in images:
                images.append(img["url"])

    for d_img in discovered_images:
        if d_img not in images:
            images.append(d_img)

    if raw_data.get("image") and isinstance(raw_data["image"], str) and raw_data["image"] not in images:
        images.append(raw_data["image"])

    if not images:
        images.append(f"https://media.jdsports.com/i/finishline/{sku}_001_P1")

    featured_image = images[0]

    # 3. Whole-Rupee INR Math (ADR 0006)
    if source_price <= 0 and parsed_sizes:
        valid_prices = [s['price_usd'] for s in parsed_sizes if s.get('price_usd', 0) > 0]
        if valid_prices:
            source_price = min(valid_prices)
    if source_price <= 0:
        source_price = 100.0
    price_inr = float(round(source_price * usd_to_inr_rate))
    compare_inr = float(round(source_compare_price * usd_to_inr_rate)) if (source_compare_price and source_compare_price > source_price) else None

    # 4. Colorway Title Suffixing Invariant
    clean_model_title = title_raw
    if color and color.lower() not in clean_model_title.lower():
        title = f"{clean_model_title} - {color}"
    else:
        title = clean_model_title

    cleaned_title = re.sub(r"['\u2019]s\b", "s", title.lower())
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', cleaned_title).strip('-')
    handle = f"{slug}-{sku.lower()}"
    source_url = raw_data.get("source_url") or raw_data.get("url") or f"https://www.jdsports.com/pdp/{slug}/{sku}"

    # 5. Build Child Variants Array
    variants = []
    for s in deduped_sizes:
        var_sku = s["sku"] or f"{sku}-{s['size_label'].replace(' ', '_')}"
        v_source_p = s["price_usd"] if s["price_usd"] > 0 else source_price
        v_inr_p = float(round(v_source_p * usd_to_inr_rate))

        variants.append({
            "id": None,
            "sku": var_sku,
            "title": f"{s['size_label']} / UK {s['uk_str']} - {color or 'Standard'}",
            "price": f"{v_inr_p:.2f}",
            "price_current": v_inr_p,
            "compare_at_price": f"{compare_inr:.2f}" if compare_inr else None,
            "source_price": v_source_p,
            "source_compare_at_price": source_compare_price,
            "currency": "INR",
            "source_currency": "USD",
            "in_stock": s["in_stock"],
            "image_url": featured_image,
            "option_values": [
                {"option_name": "Size (US)", "name": s["size_label"]},
                {"option_name": "Size (UK)", "name": f"UK {s['uk_str']}"},
                {"option_name": "Color", "name": color or "Standard"}
            ]
        })

    # 6. Parent-Variant Stock Harmony (ADR 0015)
    has_any_stock = any(v["in_stock"] for v in variants)
    availability = "in_stock" if has_any_stock else "out_of_stock"
    is_active = has_any_stock

    # 7. Specifications & Rich Description
    specs = {
        "Brand": "Nike",
        "Model": title_raw,
        "Gender": gender,
        "Sizing Category": sizing_category,
        "Color": color or "Standard",
        "Manufacturer SKU": sku,
        "Category": "Shoes",
        "Available Sizes (US)": ", ".join(s["size_label"] for s in deduped_sizes),
        "Available Sizes (UK)": ", ".join(f"UK {s['uk_str']}" for s in deduped_sizes)
    }

    raw_desc = str(raw_data.get("description") or raw_data.get("body_html") or "").strip()
    description_html = generate_description_html(title, raw_desc, sizing_category, gender, specs, deduped_sizes)

    product_options = [
        {
            "name": "Size (US)",
            "values": [{"name": s["size_label"]} for s in deduped_sizes]
        },
        {
            "name": "Size (UK)",
            "values": [{"name": f"UK {s['uk_str']}"} for s in deduped_sizes]
        },
        {
            "name": "Color",
            "values": [{"name": color or "Standard"}]
        }
    ]

    tags = [
        "Nike",
        "Footwear",
        sizing_category,
        gender,
        "JD Sports"
    ]
    if "air max" in title.lower():
        tags.append("Nike Air Max")
    elif "air force" in title.lower():
        tags.append("Nike Air Force")
    elif "dunk" in title.lower():
        tags.append("Nike Dunk Low")

    groups = [
        "footwear",
        "shoes",
        group_name,
        f"{gender.lower()}-shoes"
    ]

    # 8. Deterministic Primary Key
    product_id = hashlib.sha256(f"jdsports::{sku}".encode("utf-8")).hexdigest()[:16]
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    return {
        "id": product_id,
        "source_store": "jdsports",
        "source_url": source_url,
        "handle": handle,
        "title": title,
        "vendor": "Nike",
        "product_type": "Shoes & Footwear",
        "gender": gender,
        "sizing_category": sizing_category,
        "source_sku": sku,
        "source_price": source_price,
        "source_compare_at_price": source_compare_price,
        "current_price": price_inr,
        "compare_at_price": compare_inr,
        "currency": "INR",
        "source_currency": "USD",
        "forex_rate_used": usd_to_inr_rate,
        "availability": availability,
        "is_active": is_active,
        "material": "Leather, synthetic and textile upper with rubber traction outsole",
        "specifications": specs,
        "descriptionHtml": description_html,
        "images": images,
        "variants": variants,
        "product_options": product_options,
        "tags": tags,
        "groups": list(set(groups)),
        "created_at": now_iso,
        "updated_at": now_iso,
        "last_verified_at": now_iso
    }
