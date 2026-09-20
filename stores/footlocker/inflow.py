"""
Store Inflow Normalizer: Foot Locker (Nike Vomero Collection)
Transforms raw Foot Locker PDP hydrated data into canonical product dictionaries.
Pure functions only, zero classes (ADR 0004, ADR 0005, ADR 0006).
"""
import os
import sys
import re
import time
import hashlib
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from storage.forex import get_usd_to_inr_rate

# Nike Official US to UK and EU conversion charts
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


def parse_numeric_size(size_str: str) -> Optional[float]:
    """
    Parse numeric US shoe size float from strings like '08.5', '8.5', '10.0', 'M6.0 / W7.5'.
    Enforces adult threshold >= 3.5 to eliminate kids/youth sizing.
    Rejects standalone width indicators ('2E', '4E', 'EE', 'D', 'W', 'Wide', 'Medium').
    """
    s = str(size_str).strip()
    if not s:
        return None
    # Reject explicit youth/kid indicators
    if re.search(r'(?i)\b(?:kid|kids|toddler|youth|infant|baby|preschool|grade school)\b|\b\d+\s*y\b', s):
        return None
    # Reject standalone width codes
    if re.search(r'^(?:\d+e|ee|d|w|wide|medium|narrow|extra wide|width\s*-\s*[a-z0-9\s\-]+)$', s, re.IGNORECASE):
        return None

    # Handle dualSize like "M6.0 / W7.5"
    if "/" in s and ("M" in s or "W" in s):
        match_m = re.search(r'M\s*(\d+(?:\.\d+)?)', s)
        if match_m:
            try:
                val = float(match_m.group(1))
                return val if val >= 3.5 else None
            except ValueError:
                pass

    clean = re.sub(r'(?i)us|eu|uk', '', s).strip()
    match = re.search(r'(\d+(?:\.\d+)?)', clean)
    if match:
        try:
            val = float(match.group(1))
            return val if val >= 3.5 else None
        except ValueError:
            return None
    return None


def convert_us_to_uk(us_size: float, gender: str, brand: str = "Nike") -> str:
    """Convert US shoe size to brand-appropriate UK shoe size."""
    key = f"{us_size:g}"
    b_lower = brand.lower()
    if "adidas" in b_lower:
        if "women" in gender.lower():
            return f"{max(0.0, us_size - 1.5):g}"
        return f"{max(0.0, us_size - 0.5):g}"
    elif "asics" in b_lower:
        if "women" in gender.lower():
            return f"{max(0.0, us_size - 2.0):g}"
        return f"{max(0.0, us_size - 1.0):g}"
    else:
        # Nike and standard footwear default
        if "women" in gender.lower():
            if key in NIKE_WOMEN_US_TO_UK:
                return NIKE_WOMEN_US_TO_UK[key]
            return f"{max(0.0, us_size - 2.5):g}"
        else:
            if key in NIKE_MEN_US_TO_UK:
                return NIKE_MEN_US_TO_UK[key]
            return f"{max(0.0, us_size - 1.0):g}"


def convert_us_to_eu(us_size: float, gender: str, brand: str = "Nike") -> str:
    """Convert US shoe size to brand-appropriate EU shoe size."""
    key = f"{us_size:g}"
    b_lower = brand.lower()
    if "adidas" in b_lower:
        if "women" in gender.lower():
            return f"{34.0 + (us_size * 1.33):.1f}"
        return f"{35.0 + (us_size * 1.33):.1f}"
    elif "asics" in b_lower:
        if "women" in gender.lower():
            return f"{32.0 + (us_size * 1.25):.1f}"
        return f"{33.0 + (us_size * 1.25):.1f}"
    else:
        # Nike and standard footwear default
        if "women" in gender.lower():
            if key in NIKE_WOMEN_US_TO_EU:
                return NIKE_WOMEN_US_TO_EU[key]
            return f"{30.5 + (us_size * 1.25):.1f}"
        else:
            if key in NIKE_MEN_US_TO_EU:
                return NIKE_MEN_US_TO_EU[key]
            return f"{32.5 + (us_size * 1.25):.1f}"


def determine_gender(name: str, model_gender: Optional[List[str]] = None) -> str:
    """Determine clean gender string (Men's, Women's, Unisex)."""
    name_lower = name.lower()
    if model_gender and isinstance(model_gender, list) and model_gender:
        mg = model_gender[0].lower()
        if "women" in mg:
            return "Women's"
        if "men" in mg:
            return "Men's"
    if "women" in name_lower:
        return "Women's"
    elif "men" in name_lower:
        return "Men's"
    return "Unisex"


def generate_description_html(
    title: str,
    desc_html: str,
    gender: str,
    specs: Dict[str, Any],
    sizes: List[Dict[str, Any]],
    brand: str = "Nike"
) -> str:
    """
    Generate rich HTML body with specs table and shoe size guide accordion (ADR 0006).
    """
    clean_desc = desc_html.strip() if desc_html else f"<p>{title} provides premium cushioning and lightweight performance.</p>"
    if clean_desc.startswith("'") and clean_desc.endswith("'"):
        clean_desc = clean_desc[1:-1]
    if clean_desc.startswith('"') and clean_desc.endswith('"'):
        clean_desc = clean_desc[1:-1]

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

    # Shoe Size Conversion Accordion Table (ADR 0006)
    size_rows = "".join(
        f"<tr><td style='padding:6px 12px;text-align:center;'>US {s['us_str']}</td>"
        f"<td style='padding:6px 12px;text-align:center;'>UK {s['uk_str']}</td>"
        f"<td style='padding:6px 12px;text-align:center;'>EU {s['eu_str']}</td>"
        f"<td style='padding:6px 12px;text-align:center;'>{'In Stock' if s['in_stock'] else 'Out of Stock'}</td></tr>"
        for s in sizes
    )

    accordion_html = f"""
<details class="size-guide-accordion" style="margin: 20px 0; padding: 12px; border: 1px solid #e0e0e0; border-radius: 6px;">
  <summary style="font-weight: 600; cursor: pointer; font-size: 15px;">{brand} Size Guide &amp; Conversions ({gender})</summary>
  <div style="margin-top: 12px;">
    <p style="font-size: 13px; color: #666; margin-bottom: 8px;">Official {brand} shoe size conversion matrix (US / UK / EU):</p>
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


def parse_product_payload(
    raw_pdp_data: Dict[str, Any],
    forex_rate: Optional[float] = None,
    group_name: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Pure functional parser transforming raw Foot Locker PDP payload into canonical product format.
    Enforces whole-rupee INR pricing, zero 1-size truncation invariant, and width/size separation.
    """
    if forex_rate is None:
        forex_rate = get_usd_to_inr_rate()

    style = raw_pdp_data.get("style") or {}
    model = raw_pdp_data.get("model") or {}
    sku = str(style.get("sku") or "").strip()
    if not sku:
        return None

    brand = str(model.get("brand") or style.get("brand") or "Nike").strip()
    model_name = str(model.get("name") or style.get("name") or "Shoes").strip()
    gender = determine_gender(model_name, model.get("genders"))
    color = str(style.get("color") or "").strip()
    width_raw = str(style.get("width") or "Width - D - Medium").strip()

    # Title: Clean model name + color suffix for clear differentiation
    title = f"{model_name} - {color}" if color and color.lower() != "standard" and color.lower() not in model_name.lower() else model_name

    # 1. Pricing Extraction & Whole-Rupee INR Conversion (ADR 0006)
    price_obj = style.get("price") or {}
    source_price_usd = float(price_obj.get("salePrice") or price_obj.get("listPrice") or 0.0)
    source_regular_usd = float(price_obj.get("listPrice") or source_price_usd)
    if source_price_usd <= 0:
        return None

    price_inr = float(round(source_price_usd * forex_rate))
    compare_inr = float(round(source_regular_usd * forex_rate)) if source_regular_usd > source_price_usd else None

    # 2. Extract Full Variant Size Matrix (Anti-Truncation Standard)
    raw_sizes = raw_pdp_data.get("sizes") or []
    valid_sizes = []
    for s_entry in raw_sizes:
        raw_sz = s_entry.get("strippedSize") or s_entry.get("size")
        numeric_sz = parse_numeric_size(raw_sz)
        if numeric_sz is None:
            continue
        in_stock = bool(s_entry.get("active", False))
        uk_sz = convert_us_to_uk(numeric_sz, gender, brand)
        eu_sz = convert_us_to_eu(numeric_sz, gender, brand)
        valid_sizes.append({
            "us_size": numeric_sz,
            "us_str": f"{numeric_sz:g}",
            "uk_str": uk_sz,
            "eu_str": eu_sz,
            "in_stock": in_stock,
            "product_number": s_entry.get("productNumber")
        })

    # Deduplicate sizes by us_size, merging in_stock status
    size_map: Dict[float, Dict[str, Any]] = {}
    for s in valid_sizes:
        u_val = s["us_size"]
        if u_val not in size_map:
            size_map[u_val] = s
        else:
            if s["in_stock"]:
                size_map[u_val]["in_stock"] = True
    deduped_sizes = [size_map[k] for k in sorted(size_map.keys())]

    # Anti-Truncation Invariant: Footwear MUST have multi-size matrix (>= 2 sizes)
    if len(deduped_sizes) <= 1:
        return None

    # 3. Images Extraction & Galleries
    images: List[str] = []
    # Passed in raw_pdp_data['images'] from JSON-LD or CDN
    for img in raw_pdp_data.get("images", []):
        if img and str(img).startswith("http") and img not in images:
            images.append(img)

    base_img = style.get("imageUrl", {}).get("base")
    if base_img and base_img not in images:
        images.append(base_img)

    if not images:
        images.append(f"https://images.footlocker.com/is/image/EBFL2/{sku}")

    featured_image = images[0]

    # 4. Handle and URLs
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', title.lower()).strip('-')
    handle = f"{slug}-{sku.lower()}"
    canonical_url = f"https://www.footlocker.com/product/{slug}/{sku}.html"

    # 5. Variants Construction
    variants = []
    for s in deduped_sizes:
        var_sku = f"{sku}-{s['us_str']}"
        variants.append({
            "id": None,
            "sku": var_sku,
            "title": f"US {s['us_str']} / UK {s['uk_str']} - {color or 'Standard'}",
            "price": f"{price_inr:.2f}",
            "compare_at_price": f"{compare_inr:.2f}" if compare_inr else None,
            "source_price": source_price_usd,
            "source_compare_at_price": source_regular_usd if source_regular_usd > source_price_usd else None,
            "currency": "INR",
            "source_currency": "USD",
            "in_stock": s["in_stock"],
            "image_url": featured_image,
            "option_values": [
                {"option_name": "Size (US)", "name": f"US {s['us_str']}"},
                {"option_name": "Size (UK)", "name": f"UK {s['uk_str']}"},
                {"option_name": "Color", "name": color or "Standard"}
            ]
        })

    # Stock Harmony Invariant (ADR 0015):
    # Parent availability strictly synchronized with child variant in_stock statuses
    has_any_stock = any(v["in_stock"] for v in variants)
    availability = "in_stock" if has_any_stock else "out_of_stock"
    is_active = has_any_stock

    # 6. Specifications & Enrichment
    supplier_skus = style.get("vendorAttributes", {}).get("supplierSkus") or []
    mfg_sku = supplier_skus[0] if supplier_skus else sku
    material = "Premium upper with durable overlays and responsive traction outsole"

    specs = {
        "Brand": brand,
        "Model": model_name,
        "Gender": gender,
        "Color": color or "Standard",
        "Width": width_raw,
        "Material": material,
        "Manufacturer SKU": mfg_sku,
        "Category": "Shoes",
        "Available Sizes (US)": ", ".join(f"US {s['us_str']}" for s in deduped_sizes),
        "Available Sizes (UK)": ", ".join(f"UK {s['uk_str']}" for s in deduped_sizes)
    }

    raw_desc = model.get("description") or style.get("description") or ""
    description_html = generate_description_html(title, raw_desc, gender, specs, deduped_sizes, brand)

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
            "values": [{"name": color or "Standard"}]
        }
    ]

    # 7. Compute Primary Key: SHA256("footlocker::" + sku)[:16]
    product_id = hashlib.sha256(f"footlocker::{sku}".encode("utf-8")).hexdigest()[:16]
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    return {
        "id": product_id,
        "source_store": "footlocker",
        "source_url": canonical_url,
        "handle": handle,
        "title": title,
        "vendor": brand,
        "product_type": "Shoes",
        "source_sku": sku,
        "source_price": source_price_usd,
        "source_compare_at_price": source_regular_usd if source_regular_usd > source_price_usd else None,
        "current_price": price_inr,
        "compare_at_price": compare_inr,
        "currency": "INR",
        "source_currency": "USD",
        "forex_rate_used": forex_rate,
        "availability": availability,
        "is_active": is_active,
        "color": color,
        "width": width_raw,
        "material": material,
        "specifications": specs,
        "descriptionHtml": description_html,
        "images": images,
        "variants": variants,
        "product_options": product_options,
        "tags": [
            brand.lower(), "footwear", "shoes",
            gender.lower(), f"sizes-{len(deduped_sizes)}"
        ],
        "groups": [group_name or f"{brand} Shoes"],
        "last_verified_at": now_iso,
        "created_at": now_iso,
        "updated_at": now_iso
    }
