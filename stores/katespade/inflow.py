"""
Store Inflow Normalizer: KATE SPADE OUTLET
Transforms raw Kate Spade PDP data (from SFCC HTML / JSON-LD / API) into canonical Shopify format.
Pure functions only, zero classes (ADR 0005, ADR 0006).
"""
import re
import html
import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple
from storage.forex import convert_usd_to_inr
from storage.pricing_engine import resolve_storefront_pricing


def parse_product_payload(raw_data: Dict[str, Any], usd_to_inr_rate: float, group_name: str = "handbags") -> Dict[str, Any]:
    """
    Transform raw Kate Spade data (extracted from PDP HTML & JSON-LD) into canonical product record.
    """
    # 1. Identity & Handle
    title = clean_title(raw_data.get("title", ""))
    handle = raw_data.get("handle") or title.lower().replace(" ", "-")
    handle = re.sub(r'[^a-z0-9\-]', '', handle)
    vendor = "Kate Spade"
    product_type = raw_data.get("product_type") or determine_product_type(title, group_name)
    gender = raw_data.get("gender") or "Women"

    # 2. Base SKU & URL
    sku = raw_data.get("sku") or raw_data.get("source_sku") or f"KS-{handle[:10].upper()}"
    source_url = raw_data.get("url") or raw_data.get("source_url") or ""

    # 3. Pricing
    source_price_usd = float(raw_data.get("price") or raw_data.get("source_price") or 0.0)
    source_compare_usd = float(raw_data.get("compare_at_price") or 0.0) if raw_data.get("compare_at_price") else None
    
    price_inr = int(round(convert_usd_to_inr(source_price_usd, usd_to_inr_rate)))
    compare_inr = int(round(convert_usd_to_inr(source_compare_usd, usd_to_inr_rate))) if source_compare_usd else None

    # 4. Images (High-Resolution Adobe Scene7)
    images = clean_images(raw_data.get("images", []))
    featured_image = images[0] if images else None

    # 5. Specifications & Measurements
    specs = parse_specifications(raw_data.get("description", ""), raw_data.get("bullets", []), raw_data.get("specs", {}))
    dimensions, measurements = extract_structured_dimensions_and_measurements(
        raw_data.get("description", ""),
        raw_data.get("bullets", []),
        specs
    )
    if dimensions.get("formatted") and "Bag Dimensions" not in specs:
        specs["Bag Dimensions"] = dimensions["formatted"]
    material = specs.get("Material") or specs.get("Major Material") or raw_data.get("material") or "Refined Leather"

    # 6. Variants & Colorways
    variants = build_canonical_variants(
        raw_data=raw_data,
        base_sku=sku,
        price_inr=price_inr,
        compare_inr=compare_inr,
        source_price_usd=source_price_usd,
        source_compare_usd=source_compare_usd,
        featured_image=featured_image,
        usd_to_inr_rate=usd_to_inr_rate
    )

    # 7. Product Options
    product_options = build_product_options(variants)

    # 8. Overall Availability
    availability = "in_stock" if any(v.get("in_stock", False) for v in variants) else "out_of_stock"

    # 9. Rich Description HTML
    description_html = generate_description_html(raw_data.get("description", ""), specs)

    tags = raw_data.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    default_tags = ["Kate Spade", gender, "Handbags", product_type]
    for dt in default_tags:
        if dt not in tags:
            tags.append(dt)

    return {
        "source_store": "katespade",
        "source_url": source_url,
        "handle": handle,
        "title": title,
        "vendor": vendor,
        "product_type": product_type,
        "gender": gender,
        "source_sku": sku,
        "source_price": source_price_usd,
        "source_compare_at_price": source_compare_usd,
        "current_price": price_inr,
        "compare_at_price": compare_inr,
        "currency": "INR",
        "source_currency": "USD",
        "forex_rate_used": usd_to_inr_rate,
        "availability": availability,
        "material": material,
        "specifications": specs,
        "dimensions": dimensions,
        "measurements": measurements,
        "descriptionHtml": description_html,
        "images": images,
        "variants": variants,
        "product_options": product_options,
        "tags": tags[:20],
        "groups": [group_name],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "last_verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }


def clean_title(title: str) -> str:
    """Sanitize title string."""
    cleaned = html.unescape(title)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def determine_product_type(title: str, group_name: str) -> str:
    """Determine standardized product category."""
    t = title.lower()
    g = group_name.lower()
    if "crossbody" in t or "swingpack" in t or "camera bag" in t:
        return "Crossbody Bags"
    if "satchel" in t or "top handle" in t or "top-handle" in t or "barrel" in t:
        return "Satchels & Top Handles"
    if "tote" in t or "carryall" in t or "shopper" in t:
        return "Totes & Carryalls"
    if "shoulder" in t or "hobo" in t or "flaptote" in t:
        return "Shoulder Bags"
    if "bucket" in t:
        return "Bucket Bags"
    if "backpack" in t:
        return "Backpacks"
    if "wallet" in t or "card case" in t or "cardholder" in t or "wristlet" in t:
        return "Wallets & Small Goods"
    return "Handbags"


def clean_images(image_list: List[str]) -> List[str]:
    """Filter and sanitize Scene7 high-resolution image URLs, strictly excluding swatches."""
    urls = []
    for img in image_list:
        if not img or not isinstance(img, str):
            continue
        if "_swatch" in img.lower() or "swatch_" in img.lower():
            continue
        clean = img.split("?")[0].strip().rstrip("\\")
        if clean.startswith("//"):
            clean = f"https:{clean}"
        if clean.startswith("http") and clean not in urls:
            urls.append(clean)
    return urls


def extract_structured_dimensions_and_measurements(
    desc: str,
    bullets: List[str],
    specs: Dict[str, Any]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Extract isolated dimensions (LxHxW) and measurements (drops, strap)
    conforming to Shopify Metafield specifications.
    """
    dimensions: Dict[str, Any] = {
        "length_in": None,
        "height_in": None,
        "width_in": None,
        "formatted": None
    }
    measurements: Dict[str, Any] = {
        "handle_drop_in": None,
        "strap_drop_in": None,
        "heel_height_in": None
    }

    all_texts = list(bullets)
    if desc:
        all_texts.extend([line.strip() for line in desc.splitlines() if line.strip()])
    if "Bag Dimensions" in specs:
        all_texts.append(str(specs["Bag Dimensions"]))

    dim_pattern = re.compile(
        r'(\d+(?:\s+\d+/\d+)?|\d+(?:\.\d+)?)"\s*\(L\)\s*x\s*(\d+(?:\s+\d+/\d+)?|\d+(?:\.\d+)?)"\s*\(H\)(?:\s*x\s*(\d+(?:\s+\d+/\d+)?|\d+(?:\.\d+)?)"\s*\(W\))?',
        re.IGNORECASE
    )

    for text in all_texts:
        clean_text = html.unescape(text).strip()
        if not clean_text:
            continue

        # 1. Check Dimensions LxHxW format
        if not dimensions["formatted"]:
            m_dim = dim_pattern.search(clean_text)
            if m_dim:
                l_val = m_dim.group(1).strip()
                h_val = m_dim.group(2).strip()
                w_val = m_dim.group(3).strip() if m_dim.group(3) else None
                dimensions["length_in"] = l_val
                dimensions["height_in"] = h_val
                dimensions["width_in"] = w_val
                dimensions["formatted"] = f'{l_val}" (L) x {h_val}" (H)' + (f' x {w_val}" (W)' if w_val else '')

        # 1b. Check Key-Value Dimensions: Length: 6.5", Height: 4.5", Width: 2.5"
        if not dimensions["length_in"]:
            m_len = re.search(r'length:\s*([0-9./\s]+)"?', clean_text, re.IGNORECASE)
            if m_len:
                dimensions["length_in"] = m_len.group(1).strip()
        if not dimensions["height_in"]:
            m_hgt = re.search(r'height:\s*([0-9./\s]+)"?', clean_text, re.IGNORECASE)
            if m_hgt:
                dimensions["height_in"] = m_hgt.group(1).strip()
        if not dimensions["width_in"]:
            m_wdt = re.search(r'width:\s*([0-9./\s]+)"?', clean_text, re.IGNORECASE)
            if m_wdt:
                dimensions["width_in"] = m_wdt.group(1).strip()

        # 2. Check Handle Drop
        if not measurements["handle_drop_in"] and "handle" in clean_text.lower() and "drop" in clean_text.lower():
            m_hd = re.search(r'(\d+(?:\s+\d+/\d+)?|\d+(?:\.\d+)?)"\s*drop', clean_text, re.IGNORECASE)
            if m_hd:
                measurements["handle_drop_in"] = m_hd.group(1).strip()

        # 3. Check Strap / Crossbody Drop
        if not measurements["strap_drop_in"] and any(k in clean_text.lower() for k in ["strap", "crossbody", "shoulder"]) and "drop" in clean_text.lower():
            m_sd = re.search(r'(\d+(?:\s+\d+/\d+)?|\d+(?:\.\d+)?)"\s*drop', clean_text, re.IGNORECASE)
            if m_sd:
                measurements["strap_drop_in"] = m_sd.group(1).strip()

    if not dimensions["formatted"] and dimensions["length_in"] and dimensions["height_in"]:
        l = dimensions["length_in"]
        h = dimensions["height_in"]
        w = dimensions["width_in"]
        dimensions["formatted"] = f'{l}" (L) x {h}" (H)' + (f' x {w}" (W)' if w else '')

    return dimensions, measurements


def parse_specifications(desc: str, bullets: List[str], existing_specs: Dict[str, Any]) -> Dict[str, str]:
    """Extract key-value specifications and measurements from description and bullet points."""
    specs = dict(existing_specs) if existing_specs else {}
    
    all_bullets = list(bullets)
    if not all_bullets and desc:
        all_bullets = [b.strip() for b in desc.splitlines() if b.strip()]

    for b in all_bullets:
        clean_b = html.unescape(b).strip()
        if not clean_b:
            continue

        dim_match = re.search(r'(\d+(?:\s+\d+/\d+)?|\d+/\d+)"\s*\(L\)\s*x\s*(\d+(?:\s+\d+/\d+)?|\d+/\d+)"\s*\(H\)(?:\s*x\s*(\d+(?:\s+\d+/\d+)?|\d+/\d+)"\s*\(W\))?', clean_b, re.IGNORECASE)
        if dim_match:
            specs["Bag Dimensions"] = dim_match.group(0).strip()
            continue

        if "drop" in clean_b.lower():
            if "handle" in clean_b.lower():
                specs["Handle Drop"] = clean_b
            elif "strap" in clean_b.lower():
                specs["Shoulder Strap Drop"] = clean_b
            else:
                specs["Drop"] = clean_b
        elif "leather" in clean_b.lower() or "canvas" in clean_b.lower() or "suede" in clean_b.lower() or "saffiano" in clean_b.lower() or "nylon" in clean_b.lower() or "pvc" in clean_b.lower():
            if "Material" not in specs:
                specs["Material"] = clean_b
        elif "lining" in clean_b.lower():
            specs["Lining"] = clean_b
        elif "pocket" in clean_b.lower() or "card slot" in clean_b.lower() or "compartment" in clean_b.lower():
            specs["Pockets"] = clean_b
        elif "closure" in clean_b.lower() or "zip" in clean_b.lower() or "snap" in clean_b.lower():
            specs["Closure"] = clean_b
        elif "hardware" in clean_b.lower():
            specs["Hardware"] = clean_b
        elif "style" in clean_b.lower() and any(c.isdigit() for c in clean_b):
            specs["Style No"] = clean_b

    return specs


def build_canonical_variants(
    raw_data: Dict[str, Any],
    base_sku: str,
    price_inr: int,
    compare_inr: Optional[int],
    source_price_usd: float,
    source_compare_usd: Optional[float],
    featured_image: Optional[str],
    usd_to_inr_rate: float
) -> List[Dict[str, Any]]:
    """Build canonical multi-colorway variants from ProductGroup hasVariant or raw variants."""
    raw_has_variant = raw_data.get("hasVariant") or raw_data.get("variants") or []
    if isinstance(raw_has_variant, list) and raw_has_variant:
        color_variants = extract_color_variants_from_group(
            raw_has_variant,
            base_sku=base_sku,
            source_price_usd=source_price_usd,
            source_compare_usd=source_compare_usd,
            usd_to_inr_rate=usd_to_inr_rate,
            featured_image=featured_image
        )
        if color_variants:
            return color_variants

    # Single variant fallback
    return [{
        "id": None,
        "sku": base_sku,
        "title": "Default Title",
        "option1": "Default Title",
        "option2": None,
        "option3": None,
        "price": str(price_inr),
        "compare_at_price": str(compare_inr) if compare_inr else None,
        "source_price": source_price_usd,
        "source_compare_at_price": source_compare_usd,
        "currency": "INR",
        "source_currency": "USD",
        "in_stock": raw_data.get("availability") == "in_stock" if "availability" in raw_data else True,
        "image": featured_image,
        "image_url": featured_image,
        "images": clean_images(raw_data.get("images", [])),
        "inventory_quantity": 10 if raw_data.get("availability") != "out_of_stock" else 0
    }]


def extract_color_variants_from_group(
    has_variant: List[Dict[str, Any]],
    base_sku: str,
    source_price_usd: float,
    source_compare_usd: Optional[float],
    usd_to_inr_rate: float,
    featured_image: Optional[str]
) -> List[Dict[str, Any]]:
    """Extract canonical color variants from ProductGroup hasVariant list with distinct images and prices."""
    variants = []
    seen_colors = set()

    for idx, v in enumerate(has_variant):
        color_name = v.get("color") or v.get("name") or "Standard"
        color_clean = color_name.strip().title()
        if color_clean in seen_colors:
            continue
        seen_colors.add(color_clean)

        v_sku = v.get("sku") or f"{base_sku}-{idx+1}"
        offers = v.get("offers", {})
        if isinstance(offers, list) and offers:
            offers = offers[0]
            
        v_price_usd = float(offers.get("price") or source_price_usd or 0.0)
        v_price_inr = int(round(convert_usd_to_inr(v_price_usd, usd_to_inr_rate))) if v_price_usd > 0 else 0
        v_compare_inr = int(round(convert_usd_to_inr(source_compare_usd, usd_to_inr_rate))) if source_compare_usd else None
        
        v_avail_str = str(offers.get("availability", "InStock")).lower()
        v_stock = "instock" in v_avail_str

        # Extract hero image and multi-angle gallery for this specific colorway
        v_images_raw = v.get("image", [])
        if isinstance(v_images_raw, (str, dict)):
            v_images_raw = [v_images_raw]
            
        v_clean_images = []
        for img_obj in v_images_raw:
            u = img_obj.get("url") if isinstance(img_obj, dict) else img_obj
            if u and isinstance(u, str):
                u_clean = u.split("?")[0].strip()
                if "_swatch" not in u_clean.lower() and "swatch_" not in u_clean.lower():
                    if u_clean.startswith("//"):
                        u_clean = f"https:{u_clean}"
                    if u_clean not in v_clean_images:
                        v_clean_images.append(u_clean)

        v_hero = v_clean_images[0] if v_clean_images else featured_image

        variants.append({
            "id": None,
            "sku": v_sku,
            "title": color_clean,
            "option1": color_clean,
            "option2": None,
            "option3": None,
            "price": str(v_price_inr),
            "compare_at_price": str(v_compare_inr) if v_compare_inr else None,
            "source_price": v_price_usd,
            "source_compare_at_price": source_compare_usd,
            "currency": "INR",
            "source_currency": "USD",
            "in_stock": v_stock,
            "image": v_hero,
            "image_url": v_hero,
            "images": v_clean_images,
            "inventory_quantity": 10 if v_stock else 0
        })

    return variants


def build_product_options(variants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build Shopify-compliant product options array for color variations."""
    color_values = []
    for v in variants:
        val = v.get("option1")
        if val and val != "Default Title" and val not in color_values:
            color_values.append(val)

    if color_values:
        return [{
            "id": None,
            "name": "Color",
            "position": 1,
            "values": color_values
        }]
    return [{
        "id": None,
        "name": "Title",
        "position": 1,
        "values": ["Default Title"]
    }]


def generate_description_html(raw_desc: str, specs: Dict[str, Any]) -> str:
    """Generate rich, clean luxury HTML for product description and specification table."""
    parts = []
    
    # 1. Clean Marketing Copy
    clean_desc = html.unescape(raw_desc).strip()
    if clean_desc:
        lines = [line.strip() for line in clean_desc.splitlines() if line.strip()]
        for line in lines:
            if not any(k.lower() in line.lower() for k in ["length:", "height:", "width:", "measurements", "features", "style no", "imported"]):
                parts.append(f"<p>{line}</p>")

    # 2. Specifications Table / Accordion
    if specs:
        parts.append('<div class="product-specifications" style="margin-top: 1.5rem;">')
        parts.append('<h4 style="font-size: 0.875rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.75rem;">Specifications & Details</h4>')
        parts.append('<ul style="list-style-type: none; padding-left: 0; font-size: 0.875rem; line-height: 1.6;">')
        for k, v in specs.items():
            parts.append(f'<li><strong>{html.escape(k)}:</strong> {html.escape(str(v))}</li>')
        parts.append('</ul>')
        parts.append('</div>')

    return "\n".join(parts)
