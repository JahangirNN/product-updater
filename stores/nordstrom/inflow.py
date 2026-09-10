"""
Store Inflow Normalizer: Nordstrom (On Running Footwear)
Transforms raw Nordstrom product data (from Firecrawl JSON or scrape) into canonical Shopify format.
Pure functions only, zero classes (ADR 0004, ADR 0005, ADR 0006).
"""
import re
import html
import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple
from storage.forex import convert_usd_to_inr

# Conversion Tables derived from Nordstrom official On conversion guides
WOMEN_US_TO_UK = {
    "4": "2", "4.0": "2", "4.5": "2.5",
    "5": "3", "5.0": "3", "5.5": "3.5",
    "6": "4", "6.0": "4", "6.5": "4.5",
    "7": "5", "7.0": "5", "7.5": "5.5",
    "8": "6", "8.0": "6", "8.5": "6.5",
    "9": "7", "9.0": "7", "9.5": "7.5",
    "10": "8", "10.0": "8", "10.5": "8.5",
    "11": "9", "11.0": "9", "11.5": "9.5",
    "12": "10", "12.0": "10", "12.5": "10.5",
    "13": "11", "13.0": "11", "14": "11.5", "14.0": "11.5"
}

WOMEN_US_TO_EU = {
    "4": "35", "4.0": "35", "4.5": "35.5",
    "5": "36", "5.0": "36", "5.5": "36.5",
    "6": "37", "6.0": "37", "6.5": "37.5",
    "7": "38", "7.0": "38", "7.5": "38.5",
    "8": "39", "8.0": "39", "8.5": "40",
    "9": "40.5", "9.0": "40.5", "9.5": "41",
    "10": "42", "10.0": "42", "10.5": "42.5",
    "11": "43", "11.0": "43", "11.5": "44",
    "12": "44.5", "12.0": "44.5", "12.5": "45",
    "13": "46", "13.0": "46", "14": "47", "14.0": "47"
}

MEN_US_TO_UK = {
    "5": "4.5", "5.0": "4.5", "5.5": "5",
    "6": "5.5", "6.0": "5.5", "6.5": "6",
    "7": "6.5", "7.0": "6.5", "7.5": "7",
    "8": "7.5", "8.0": "7.5", "8.5": "8",
    "9": "8.5", "9.0": "8.5", "9.5": "9",
    "10": "9.5", "10.0": "9.5", "10.5": "10",
    "11": "10.5", "11.0": "10.5", "11.5": "11",
    "12": "11.5", "12.0": "11.5", "12.5": "12",
    "13": "12.5", "13.0": "12.5", "13.5": "13",
    "14": "13.5", "14.0": "13.5", "14.5": "14",
    "15": "14.5", "15.0": "14.5"
}

MEN_US_TO_EU = {
    "5": "37.5", "5.0": "37.5", "5.5": "38",
    "6": "38.5", "6.0": "38.5", "6.5": "39",
    "7": "40", "7.0": "40", "7.5": "40.5",
    "8": "41", "8.0": "41", "8.5": "42",
    "9": "42.5", "9.0": "42.5", "9.5": "43",
    "10": "44", "10.0": "44", "10.5": "44.5",
    "11": "45", "11.0": "45", "11.5": "46",
    "12": "47", "12.0": "47", "12.5": "47.5",
    "13": "48", "13.0": "48", "13.5": "48.5",
    "14": "49", "14.0": "49", "14.5": "49.5",
    "15": "50", "15.0": "50"
}


def parse_numeric_size(size_str: str) -> Optional[float]:
    """Parse numeric US shoe size float from strings like '7', '8.5', '7 1/2', 'US 9.5', '10.5US - 44 EU'."""
    s = str(size_str).strip()
    # Reject explicit youth/kid indicators when parsing adult shoe sizes
    if re.search(r'(?i)\b(?:kid|kids|toddler|youth|infant|baby)\b|\b\d+\s*y\b', s):
        return None
    clean = re.sub(r'(?i)us|eu|uk', '', s).strip()
    clean = clean.replace('½', ' 1/2')

    # Match fractional sizes like "7 1/2"
    frac_match = re.search(r'(\d+)\s+1/2', clean)
    if frac_match:
        try:
            return float(frac_match.group(1)) + 0.5
        except ValueError:
            pass

    match = re.search(r'(\d+(?:\.\d+)?)', clean)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def convert_us_to_uk(us_size: float, gender: str) -> str:
    """Convert US shoe size to UK shoe size for On running footwear."""
    key = f"{us_size:g}"
    gender_lower = gender.lower()
    if "women" in gender_lower:
        if key in WOMEN_US_TO_UK:
            return WOMEN_US_TO_UK[key]
        return f"{max(0.0, us_size - 2.0):g}"
    else:
        # Men and Unisex default to Men's chart
        if key in MEN_US_TO_UK:
            return MEN_US_TO_UK[key]
        if us_size >= 14.0:
            return f"{us_size - 0.5:g}"
        return f"{max(0.0, us_size - 0.5):g}"


def convert_us_to_eu(us_size: float, gender: str) -> str:
    """Convert US shoe size to EU shoe size for On running footwear."""
    key = f"{us_size:g}"
    gender_lower = gender.lower()
    if "women" in gender_lower:
        if key in WOMEN_US_TO_EU:
            return WOMEN_US_TO_EU[key]
        return f"{31.0 + (us_size * 1.0):g}"
    else:
        if key in MEN_US_TO_EU:
            return MEN_US_TO_EU[key]
        return f"{33.0 + (us_size * 1.0):g}"


def is_kids_product(
    title: str,
    url: str,
    raw_gender: Optional[str] = None,
    sizes: Optional[List[Any]] = None
) -> bool:
    """Detect kids, toddler, or youth products to enforce strict adult Men/Women/Unisex boundary."""
    combined = f"{raw_gender or ''} {title} {url}".lower()
    leak_keywords = [
        "kid", "kids", "toddler", "youth", "baby", "infant", 
        "little-kid", "big-kid", "child", "children"
    ]
    if any(k in combined for k in leak_keywords):
        return True

    if sizes:
        for s in sizes:
            s_str = str(s.get("us_size") or s.get("US") if isinstance(s, dict) else s).lower()
            if any(k in s_str for k in leak_keywords) or re.search(r'\b\d+\s*y\b', s_str):
                return True

    return False


def determine_gender(title: str, url: str, raw_gender: Optional[str] = None) -> str:
    """Identify product gender classification."""
    combined = f"{raw_gender or ''} {title} {url}".lower()
    if "women" in combined:
        return "Women"
    elif "unisex" in combined:
        return "Unisex"
    elif "men" in combined:
        return "Men"
    return "Unisex"


def clean_title(title: str) -> str:
    """Clean product title and remove retail artifacts."""
    cleaned = html.unescape(title or "").strip()
    cleaned = re.sub(r'\s*\|\s*Nordstrom.*$', '', cleaned)
    # We remove the forced "On " prefix to match the live title exactly.
    return cleaned.strip()


def parse_product_payload(
    raw_data: Dict[str, Any],
    usd_to_inr_rate: float,
    group_name: str = "shoes",
    min_size_variants: int = 7,
    min_us_size: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    """
    Transform raw Nordstrom product data into canonical Shopify product dictionary.
    Enforces strict filter: ONLY products that offer at least min_size_variants (default 7) distinct size variants.
    Includes all available sizes for matching products, mapping each US size to its UK equivalent.
    Returns None if product has fewer than min_size_variants distinct sizes or is a kids/toddler category leak.
    """
    title = clean_title(raw_data.get("title", "") or raw_data.get("productTitle", ""))
    if not title or title.strip() == "On":
        return None

    url = raw_data.get("url") or raw_data.get("source_url") or raw_data.get("sourceURL") or ""
    raw_gender = raw_data.get("gender")

    raw_sizes = raw_data.get("sizes") or []

    # Strict Category Boundary: Reject Kids/Toddler/Youth items
    if is_kids_product(title, url, raw_gender, raw_sizes):
        return None

    gender = determine_gender(title, url, raw_gender)
    
    # 1. Price extraction
    source_price_usd = 0.0
    if "current_price" in raw_data and raw_data["current_price"]:
        source_price_usd = float(raw_data["current_price"])
    elif "prices" in raw_data and isinstance(raw_data["prices"], dict):
        source_price_usd = float(raw_data["prices"].get("amount", 0.0))
    elif "price" in raw_data:
        source_price_usd = float(raw_data["price"])

    if source_price_usd <= 0:
        return None

    compare_price_usd = None
    if "regular_price" in raw_data and raw_data["regular_price"]:
        compare_price_usd = float(raw_data["regular_price"])
    elif "previous_price" in raw_data and raw_data["previous_price"]:
        compare_price_usd = float(raw_data["previous_price"])

    price_inr = convert_usd_to_inr(source_price_usd, usd_to_inr_rate)
    compare_inr = convert_usd_to_inr(compare_price_usd, usd_to_inr_rate) if compare_price_usd else None

    # 2. Extract and resolve all available sizes
    raw_sizes = raw_data.get("sizes", [])
    valid_sizes = []

    for s_entry in raw_sizes:
        if isinstance(s_entry, dict):
            us_val = parse_numeric_size(s_entry.get("us_size") or s_entry.get("US") or "")
            in_stock = s_entry.get("in_stock")
            if in_stock is None:
                in_stock = s_entry.get("availability", True)
            uk_val = s_entry.get("uk_size") or s_entry.get("UK")
            eu_val = s_entry.get("eu_size") or s_entry.get("EU")
        else:
            us_val = parse_numeric_size(str(s_entry))
            in_stock = True
            uk_val = None
            eu_val = None

        if us_val is not None:
            if min_us_size is not None and us_val < min_us_size:
                continue
            resolved_uk = convert_us_to_uk(us_val, gender)
            resolved_eu = convert_us_to_eu(us_val, gender)
            valid_sizes.append({
                "us_size": us_val,
                "us_str": f"{us_val:g}",
                "uk_str": resolved_uk,
                "eu_str": resolved_eu,
                "in_stock": bool(in_stock)
            })

    # Deduplicate sizes by us_size, merging in_stock availability
    size_map: Dict[float, Dict[str, Any]] = {}
    for s in valid_sizes:
        val = s["us_size"]
        if val not in size_map:
            size_map[val] = s
        else:
            if s["in_stock"]:
                size_map[val]["in_stock"] = True
    deduped_sizes = [size_map[k] for k in sorted(size_map.keys())]

    # Strict constraint: Must offer at least min_size_variants (default 7) distinct size options
    if len(deduped_sizes) < min_size_variants:
        return None

    # 3. Colors and Images
    raw_colors = raw_data.get("colors")
    if isinstance(raw_colors, list) and raw_colors:
        colors = raw_colors
    else:
        colors = ["Standard"]
    primary_color = colors[0]

    images = clean_images(raw_data)
    featured_image = images[0] if images else None

    # 4. Handle and Style ID
    details = raw_data.get("details") or {}
    item_num = details.get("item_number") or raw_data.get("item_number") or ""
    style_id = details.get("style_id") or raw_data.get("style_id") or ""
    
    url_match = re.search(r'/s/([a-zA-Z0-9\-_]+)/(\d+)', url)
    if url_match:
        handle = url_match.group(1)
        source_id = url_match.group(2)
    else:
        handle = re.sub(r'[^a-zA-Z0-9]+', '-', title.lower()).strip('-')
        source_id = style_id or item_num or "7897718"

    sku_root = f"ON-{source_id}"

    # 5. Variants Construction (one variant per size >= 7.0, carrying US and UK size)
    variants = []
    for idx, s in enumerate(deduped_sizes):
        var_sku = f"{sku_root}-{s['us_str']}"
        variants.append({
            "id": int(f"{source_id}{idx:02d}") if source_id.isdigit() else None,
            "sku": var_sku,
            "title": f"US {s['us_str']} / UK {s['uk_str']} - {primary_color}",
            "price": f"{price_inr:.2f}",
            "compare_at_price": f"{compare_inr:.2f}" if compare_inr and compare_inr > price_inr else None,
            "source_price": source_price_usd,
            "source_compare_at_price": compare_price_usd,
            "currency": "INR",
            "source_currency": "USD",
            "in_stock": s["in_stock"],
            "image_url": featured_image,
            "option_values": [
                {"option_name": "Size (US)", "name": f"US {s['us_str']}"},
                {"option_name": "Size (UK)", "name": f"UK {s['uk_str']}"},
                {"option_name": "Color", "name": primary_color}
            ]
        })

    # 6. Specifications and Details
    materials = details.get("materials") or raw_data.get("materials") or "Textile and synthetic upper/rubber sole"
    if isinstance(materials, list):
        materials = " / ".join(materials)
    
    specs = {
        "Brand": "On",
        "Gender": gender,
        "Category": "Footwear",
        "Material": materials,
        "Midsole Drop": details.get("midsole_drop", "8mm"),
        "Cushioning": details.get("cushioning", "CloudTec buoyant cushioning"),
        "Item Number": item_num or source_id,
        "Available Sizes (US)": ", ".join(f"US {s['us_str']}" for s in deduped_sizes),
        "Available Sizes (UK)": ", ".join(f"UK {s['uk_str']}" for s in deduped_sizes)
    }

    # 7. Rich Description HTML with Size Guide Accordion
    description_text = raw_data.get("description") or raw_data.get("productDescription") or ""
    description_html = generate_description_html(title, description_text, gender, specs, deduped_sizes)

    # 8. Product Options
    product_options = [
        {
            "name": "Size (US)",
            "values": [{"name": f"US {s['us_str']}"} for s in deduped_sizes]
        },
        {
            "name": "Size (UK)",
            "values": [{"name": f"UK {s['uk_str']}"} for s in deduped_sizes]
        },
        {
            "name": "Color",
            "values": [{"name": c} for c in colors[:5]]
        }
    ]

    availability = "in_stock" if any(v["in_stock"] for v in variants) else "out_of_stock"

    # 9. Compute Primary Key: SHA256("nordstrom::" + source_sku)[:16]
    primary_sku = variants[0]["sku"] if variants else sku_root
    product_id = hashlib.sha256(f"nordstrom::{primary_sku}".encode("utf-8")).hexdigest()[:16]
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    return {
        "id": product_id,
        "source_store": "nordstrom",
        "source_url": url,
        "handle": handle,
        "title": title,
        "vendor": "On",
        "product_type": "Athletic Shoes",
        "source_sku": primary_sku,
        "source_price": source_price_usd,
        "source_compare_at_price": compare_price_usd,
        "current_price": price_inr,
        "compare_at_price": compare_inr,
        "currency": "INR",
        "source_currency": "USD",
        "forex_rate_used": usd_to_inr_rate,
        "availability": availability,
        "material": materials,
        "specifications": specs,
        "descriptionHtml": description_html,
        "images": images,
        "variants": variants,
        "product_options": product_options,
        "tags": [
            "on-shoes", "footwear", "sneakers", "running",
            gender.lower(), f"sizes-{len(deduped_sizes)}"
        ],
        "groups": [group_name],
        "last_verified_at": now_iso,
        "created_at": now_iso,
        "updated_at": now_iso
    }


from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def clean_images(raw_data: Dict[str, Any]) -> List[str]:
    """Clean and filter high-resolution CDN images."""
    urls = []
    raw_images = raw_data.get("images") or raw_data.get("imageURLs") or []
    for img in raw_images:
        src = ""
        if isinstance(img, dict):
            src = img.get("src") or img.get("url", "")
        elif isinstance(img, str):
            src = img
        if src.startswith("//"):
            src = f"https:{src}"
        if src.startswith("http") and "svg" not in src:
            # Upgrade thumbnail dimensions to high resolution
            parsed = urlparse(src)
            if parsed.query:
                query_params = parse_qs(parsed.query, keep_blank_values=True)
                for k in ["h", "w", "width", "height"]:
                    query_params.pop(k, None)
                new_query = urlencode(query_params, doseq=True)
                src = urlunparse(parsed._replace(query=new_query))
            if src not in urls:
                urls.append(src)
    return urls


def generate_description_html(
    title: str,
    desc: str,
    gender: str,
    specs: Dict[str, str],
    sizes: List[Dict[str, Any]]
) -> str:
    """
    Format clean HTML body with an integrated Size & Dimensions accordion.
    100% compliant with ADR 0006 and universal Shopify themes.
    """
    clean_desc = html.unescape(desc or "").strip()
    material = specs.get("Material", "Textile and synthetic upper")
    drop = specs.get("Midsole Drop", "8mm")
    cushioning = specs.get("Cushioning", "CloudTec buoyant cushioning")

    rows_html = ""
    for s in sizes:
        rows_html += f"""        <tr style="border-bottom: 1px solid #f0f0f0;">
          <td style="padding: 6px; font-weight: 600;">US {s['us_str']}</td>
          <td style="padding: 6px; color: #191a1b; font-weight: 600;">UK {s['uk_str']}</td>
          <td style="padding: 6px; color: #666;">EU {s['eu_str']}</td>
          <td style="padding: 6px; color: {'#0d8a43' if s['in_stock'] else '#c92a2a'};">{'In Stock' if s['in_stock'] else 'Sold Out'}</td>
        </tr>\n"""

    out_html = f"""<div class="product-description">
  <p class="product-summary">{html.escape(clean_desc)}</p>
  
  <div class="product-highlights">
    <h4>Performance Specifications</h4>
    <ul>
      <li><strong>Brand:</strong> On Running</li>
      <li><strong>Gender:</strong> {html.escape(gender)}</li>
      <li><strong>Material:</strong> {html.escape(material)}</li>
      <li><strong>Midsole Drop:</strong> {html.escape(drop)}</li>
      <li><strong>Cushioning:</strong> {html.escape(cushioning)}</li>
    </ul>
  </div>

  <details class="size-guide-accordion" style="margin-top: 15px; border: 1px solid #e5e5e5; border-radius: 6px; padding: 10px;">
    <summary style="font-weight: bold; cursor: pointer;">📏 On Running Shoe Size & Conversion Guide ({html.escape(gender)})</summary>
    <p style="font-size: 13px; color: #666; margin: 8px 0 4px 0;">Official size conversion guide. Showing all available shoe sizes.</p>
    <table style="width: 100%; margin-top: 10px; border-collapse: collapse; font-size: 14px;">
      <thead>
        <tr style="background-color: #f8f9fa; text-align: left; border-bottom: 2px solid #ddd;">
          <th style="padding: 6px;">US Size</th>
          <th style="padding: 6px;">UK Size</th>
          <th style="padding: 6px;">EU Size</th>
          <th style="padding: 6px;">Availability</th>
        </tr>
      </thead>
      <tbody>
{rows_html}      </tbody>
    </table>
  </details>
</div>"""
    return out_html
