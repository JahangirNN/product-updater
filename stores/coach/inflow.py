"""
Store Inflow Normalizer: COACH
Transforms raw Coach PDP data (from Demandware HTML / JSON-LD / API) into canonical Shopify format.
Pure functions only, zero classes (ADR 0005, ADR 0006).
"""
import re
import html
import hashlib
from typing import Any, Dict, List, Optional
from storage.forex import convert_usd_to_inr


MEN_SHOE_CONVERSION = {
    "7": "6.5", "7.5": "7", "8": "7.5", "8.5": "8", "9": "8.5", "9.5": "9",
    "10": "9.5", "10.5": "10", "11": "10.5", "11.5": "11", "12": "11.5", "13": "12.5"
}

WOMEN_SHOE_CONVERSION = {
    "5": "3", "5.5": "3.5", "6": "4", "6.5": "4.5", "7": "5", "7.5": "5.5",
    "8": "6", "8.5": "6.5", "9": "7", "9.5": "7.5", "10": "8", "11": "9"
}


def parse_product_payload(raw_data: Dict[str, Any], usd_to_inr_rate: float, group_name: str = "bags") -> Dict[str, Any]:
    """
    Transform raw Coach data (extracted from PDP HTML & JSON-LD) into canonical product record.
    """
    # 1. Identity & Handle
    title = clean_title(raw_data.get("title", ""))
    handle = raw_data.get("handle") or title.lower().replace(" ", "-")
    handle = re.sub(r'[^a-z0-9\-]', '', handle)
    vendor = "COACH"
    product_type = raw_data.get("product_type") or determine_product_type(title, group_name)
    gender = raw_data.get("gender") or ("Women" if "women" in group_name.lower() else "Men")

    # 2. Base SKU & URL
    sku = raw_data.get("sku") or raw_data.get("source_sku") or f"COACH-{handle[:10].upper()}"
    source_url = raw_data.get("url") or raw_data.get("source_url") or ""

    # 3. Pricing
    source_price_usd = float(raw_data.get("price") or raw_data.get("source_price") or 0.0)
    source_compare_usd = float(raw_data.get("compare_at_price") or 0.0) if raw_data.get("compare_at_price") else None
    
    price_inr = convert_usd_to_inr(source_price_usd, usd_to_inr_rate)
    compare_inr = convert_usd_to_inr(source_compare_usd, usd_to_inr_rate) if source_compare_usd else None

    # 4. Images (High-Resolution Adobe Scene7)
    images = clean_images(raw_data.get("images", []))
    featured_image = images[0] if images else None

    # 5. Specifications & Measurements
    specs = parse_specifications(raw_data.get("description", ""), raw_data.get("bullets", []), raw_data.get("specs", {}))
    material = specs.get("Material") or specs.get("Major Material") or "Refined Leather"

    # 6. Variants & Sizing
    is_shoe = "shoe" in group_name.lower() or "shoe" in product_type.lower() or "clog" in title.lower() or "boot" in title.lower() or "loafer" in title.lower()
    variants = build_canonical_variants(
        raw_data=raw_data,
        base_sku=sku,
        price_inr=price_inr,
        compare_inr=compare_inr,
        source_price_usd=source_price_usd,
        source_compare_usd=source_compare_usd,
        is_shoe=is_shoe,
        gender=gender,
        featured_image=featured_image
    )

    # 7. Product Options
    product_options = build_product_options(variants, is_shoe)

    # 8. Overall Availability
    availability = "in_stock" if any(v.get("in_stock", False) for v in variants) else "out_of_stock"

    # 9. Rich Description HTML with Size Guide Accordion
    description_html = generate_description_html(raw_data.get("description", ""), specs, is_shoe, gender)

    tags = raw_data.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    default_tags = ["COACH", gender, product_type]
    for dt in default_tags:
        if dt not in tags:
            tags.append(dt)

    return {
        "source_store": "coach",
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
    if "wallet" in t or "wallet" in g or "card case" in t or "billfold" in t:
        return "Wallets & Small Goods"
    if "wristlet" in t or "wristlet" in g:
        return "Wristlets"
    if "shoe" in t or "shoe" in g or "boot" in t or "clog" in t or "loafer" in t or "sneaker" in t:
        return "Shoes & Footwear"
    if "backpack" in t or "backpack" in g:
        return "Backpacks"
    if "tote" in t or "carryall" in t:
        return "Tote Bags"
    if "crossbody" in t:
        return "Crossbody Bags"
    if "shoulder" in t:
        return "Shoulder Bags"
    if "satchel" in t:
        return "Satchels"
    return "Handbags"


def clean_images(image_list: List[str]) -> List[str]:
    """Filter and sanitize Scene7 high-resolution image URLs."""
    urls = []
    for img in image_list:
        if not img or not isinstance(img, str):
            continue
        clean = img.split("?")[0].strip().rstrip("\\")
        if clean.startswith("//"):
            clean = f"https:{clean}"
        if clean.startswith("http") and clean not in urls:
            urls.append(clean)
    return urls


def parse_specifications(desc: str, bullets: List[str], existing_specs: Dict[str, Any]) -> Dict[str, str]:
    """Extract key-value specifications and measurements from description and bullet points."""
    specs = dict(existing_specs) if existing_specs else {}
    
    # 1. Parse bullet points
    all_bullets = list(bullets)
    if not all_bullets and desc:
        all_bullets = [b.strip() for b in desc.splitlines() if b.strip()]

    for b in all_bullets:
        clean_b = html.unescape(b).strip()
        if not clean_b:
            continue
        # Dimensions pattern: e.g. 9 1/2" (L) x 6" (H) x 3" (W)
        dim_match = re.search(r'(\d+[\s\d/.]*"\s*\(L\)\s*x\s*\d+[\s\d/.]*"\s*\(H\)\s*x\s*\d+[\s\d/.]*"\s*\(W\))', clean_b, re.IGNORECASE)
        if dim_match:
            specs["Bag Dimensions"] = dim_match.group(1).strip()
            continue

        # Simple LxHxW
        dim_match2 = re.search(r'(\d+[\s\d/.]*"\s*x\s*\d+[\s\d/.]*"\s*x\s*\d+[\s\d/.]*")', clean_b, re.IGNORECASE)
        if dim_match2 and "Bag Dimensions" not in specs:
            specs["Bag Dimensions"] = dim_match2.group(1).strip()
            continue

        if "drop" in clean_b.lower():
            if "handle" in clean_b.lower():
                specs["Handle Drop"] = clean_b
            elif "strap" in clean_b.lower():
                specs["Shoulder Strap Drop"] = clean_b
            else:
                specs["Drop"] = clean_b
        elif "leather" in clean_b.lower() or "canvas" in clean_b.lower() or "suede" in clean_b.lower() or "cotton" in clean_b.lower() or "denim" in clean_b.lower():
            if "Material" not in specs:
                specs["Material"] = clean_b
        elif "lining" in clean_b.lower():
            specs["Lining"] = clean_b
        elif "pocket" in clean_b.lower() or "compartment" in clean_b.lower():
            specs["Pockets"] = clean_b
        elif "closure" in clean_b.lower() or "zip" in clean_b.lower() or "snap" in clean_b.lower():
            specs["Closure"] = clean_b
        elif "heel" in clean_b.lower():
            specs["Heel Height"] = clean_b
        elif "style no" in clean_b.lower():
            specs["Style No"] = clean_b

    # Fallback to structured dimensions if available
    if "Bag Dimensions" not in specs:
        w = specs.get("width")
        h = specs.get("height")
        d = specs.get("depth")
        if w and h and d:
            specs["Bag Dimensions"] = f'{d}" (L) x {h}" (H) x {w}" (W)'

    return specs


def build_canonical_variants(
    raw_data: Dict[str, Any],
    base_sku: str,
    price_inr: int,
    compare_inr: Optional[int],
    source_price_usd: float,
    source_compare_usd: Optional[float],
    is_shoe: bool,
    gender: str,
    featured_image: Optional[str]
) -> List[Dict[str, Any]]:
    """Build canonical variants for both shoes (multi-size) and accessories (colors)."""
    raw_variants = raw_data.get("variants", [])
    raw_shoe_sizes = raw_data.get("shoe_sizes", [])
    
    variants = []

    if is_shoe and raw_shoe_sizes:
        conversion_table = MEN_SHOE_CONVERSION if gender == "Men" else WOMEN_SHOE_CONVERSION
        for s_info in raw_shoe_sizes:
            us_size = str(s_info.get("size", "")).strip()
            uk_size = conversion_table.get(us_size, us_size)
            in_stock = bool(s_info.get("in_stock", True))
            v_sku = f"{base_sku}-{us_size}"
            
            variants.append({
                "id": None,
                "sku": v_sku,
                "title": f"US {us_size} / UK {uk_size}",
                "price": f"{price_inr:.2f}",
                "compare_at_price": f"{compare_inr:.2f}" if compare_inr and compare_inr > price_inr else None,
                "source_price": source_price_usd,
                "source_compare_at_price": source_compare_usd,
                "currency": "INR",
                "source_currency": "USD",
                "in_stock": in_stock,
                "image_url": featured_image,
                "option_values": [
                    {"option_name": "Size", "name": f"US {us_size} / UK {uk_size}"}
                ]
            })
    elif raw_variants:
        for idx, rv in enumerate(raw_variants):
            v_sku = rv.get("sku") or f"{base_sku}-{idx+1}"
            v_color = rv.get("color") or raw_data.get("color") or "Standard"
            v_size = rv.get("size")
            v_stock = bool(rv.get("in_stock", True))
            v_title = rv.get("name") or v_color
            
            option_vals = [{"option_name": "Color", "name": v_color}]
            if v_size and is_shoe:
                option_vals.append({"option_name": "Size", "name": v_size})

            variants.append({
                "id": rv.get("id"),
                "sku": v_sku,
                "title": v_title,
                "price": f"{price_inr:.2f}",
                "compare_at_price": f"{compare_inr:.2f}" if compare_inr and compare_inr > price_inr else None,
                "source_price": source_price_usd,
                "source_compare_at_price": source_compare_usd,
                "currency": "INR",
                "source_currency": "USD",
                "in_stock": v_stock,
                "image_url": rv.get("image") or featured_image,
                "option_values": option_vals
            })
    else:
        # Single default variant
        color_name = raw_data.get("color") or "Standard"
        variants.append({
            "id": None,
            "sku": base_sku,
            "title": color_name,
            "price": f"{price_inr:.2f}",
            "compare_at_price": f"{compare_inr:.2f}" if compare_inr and compare_inr > price_inr else None,
            "source_price": source_price_usd,
            "source_compare_at_price": source_compare_usd,
            "currency": "INR",
            "source_currency": "USD",
            "in_stock": bool(raw_data.get("available", True)),
            "image_url": featured_image,
            "option_values": [
                {"option_name": "Color", "name": color_name}
            ]
        })

    return variants


def build_product_options(variants: List[Dict[str, Any]], is_shoe: bool) -> List[Dict[str, Any]]:
    """Generate product_options structure conforming to ADR 0004."""
    options = []
    if is_shoe:
        size_values = [{"name": v["title"]} for v in variants]
        options.append({"name": "Size", "values": size_values})
    else:
        color_values = []
        seen = set()
        for v in variants:
            c = v.get("option_values", [{}])[0].get("name", "Standard")
            if c not in seen:
                seen.add(c)
                color_values.append({"name": c})
        options.append({"name": "Color", "values": color_values})
    return options


def generate_description_html(desc: str, specs: Dict[str, str], is_shoe: bool, gender: str) -> str:
    """Format clean Shopify-ready HTML body with an integrated Size Guide Accordion."""
    clean_desc = html.unescape(desc).strip()
    material = specs.get("Material", "Refined Leather")
    dims = specs.get("Bag Dimensions", "N/A")
    handle_drop = specs.get("Handle Drop", "N/A")
    strap_drop = specs.get("Shoulder Strap Drop", "N/A")
    pockets = specs.get("Pockets", "N/A")
    closure = specs.get("Closure", "N/A")
    lining = specs.get("Lining", "Fabric / Polyester")

    if is_shoe:
        heel = specs.get("Heel Height", "Standard")
        out_html = f"""<div class="product-description">
  <p class="product-summary">{html.escape(clean_desc)}</p>
  
  <div class="product-highlights">
    <h4>Product Specifications</h4>
    <ul>
      <li><strong>Upper Material:</strong> {html.escape(material)}</li>
      <li><strong>Lining:</strong> {html.escape(lining)}</li>
      <li><strong>Heel / Sole:</strong> {html.escape(heel)}</li>
    </ul>
  </div>

  <details class="size-guide-accordion" style="margin-top: 15px; border: 1px solid #e5e5e5; border-radius: 6px; padding: 10px;">
    <summary style="font-weight: bold; cursor: pointer;">📏 Official COACH {html.escape(gender)} Footwear Size Guide</summary>
    <table style="width: 100%; margin-top: 10px; border-collapse: collapse; font-size: 14px; text-align: left;">
      <thead>
        <tr style="background: #f8f8f8; border-bottom: 2px solid #ddd;">
          <th style="padding: 6px;">US Size</th>
          <th style="padding: 6px;">UK Size</th>
          <th style="padding: 6px;">Fit / Width</th>
        </tr>
      </thead>
      <tbody>
        <tr style="border-bottom: 1px solid #eee;"><td style="padding: 6px;">US 7</td><td style="padding: 6px;">UK 6.5</td><td style="padding: 6px;">Standard (D)</td></tr>
        <tr style="border-bottom: 1px solid #eee;"><td style="padding: 6px;">US 8</td><td style="padding: 6px;">UK 7.5</td><td style="padding: 6px;">Standard (D)</td></tr>
        <tr style="border-bottom: 1px solid #eee;"><td style="padding: 6px;">US 9</td><td style="padding: 6px;">UK 8.5</td><td style="padding: 6px;">Standard (D)</td></tr>
        <tr style="border-bottom: 1px solid #eee;"><td style="padding: 6px;">US 10</td><td style="padding: 6px;">UK 9.5</td><td style="padding: 6px;">Standard (D)</td></tr>
        <tr style="border-bottom: 1px solid #eee;"><td style="padding: 6px;">US 11</td><td style="padding: 6px;">UK 10.5</td><td style="padding: 6px;">Standard (D)</td></tr>
        <tr><td style="padding: 6px;">US 12</td><td style="padding: 6px;">UK 11.5</td><td style="padding: 6px;">Standard (D)</td></tr>
      </tbody>
    </table>
  </details>
</div>"""
    else:
        out_html = f"""<div class="product-description">
  <p class="product-summary">{html.escape(clean_desc)}</p>
  
  <div class="product-highlights">
    <h4>Product Specifications</h4>
    <ul>
      <li><strong>Material:</strong> {html.escape(material)}</li>
      <li><strong>Lining:</strong> {html.escape(lining)}</li>
      <li><strong>Closure:</strong> {html.escape(closure)}</li>
      <li><strong>Organization:</strong> {html.escape(pockets)}</li>
    </ul>
  </div>

  <details class="size-guide-accordion" style="margin-top: 15px; border: 1px solid #e5e5e5; border-radius: 6px; padding: 10px;">
    <summary style="font-weight: bold; cursor: pointer;">📏 Size & Measurement Guide</summary>
    <table style="width: 100%; margin-top: 10px; border-collapse: collapse; font-size: 14px;">
      <tbody>
        <tr style="border-bottom: 1px solid #f0f0f0;">
          <td style="padding: 6px; font-weight: 600;">Dimensions (L x H x W)</td>
          <td style="padding: 6px;">{html.escape(dims)}</td>
        </tr>
        <tr style="border-bottom: 1px solid #f0f0f0;">
          <td style="padding: 6px; font-weight: 600;">Handle Drop</td>
          <td style="padding: 6px;">{html.escape(handle_drop)}</td>
        </tr>
        <tr>
          <td style="padding: 6px; font-weight: 600;">Shoulder / Crossbody Strap Drop</td>
          <td style="padding: 6px;">{html.escape(strap_drop)}</td>
        </tr>
      </tbody>
    </table>
  </details>
</div>"""

    return out_html
