"""
Store Inflow Normalizer: JW PEI
Transforms raw JW PEI data (from Firecrawl or JSON endpoint) into canonical Shopify format.
Pure functions only, zero classes (ADR 0005).
"""
import re
import html
from typing import Any, Dict, List, Optional
from storage.forex import convert_usd_to_inr


def parse_product_payload(raw_data: Dict[str, Any], usd_to_inr_rate: float, group_name: str = "handbags") -> Dict[str, Any]:
    """
    Transform raw JW PEI JSON/scrape data into canonical product record.
    """
    # 1. Identity & Handle
    title = clean_title(raw_data.get("title", ""))
    handle = raw_data.get("handle") or title.lower().replace(" ", "-")
    vendor = raw_data.get("vendor") or "JW PEI"
    product_type = raw_data.get("product_type") or raw_data.get("type") or "Handbags"

    # 2. Raw variants and pricing
    raw_variants = raw_data.get("variants", [])
    first_var = raw_variants[0] if raw_variants else {}
    
    # Handle both cents and dollar formats
    price_val = raw_data.get("price")
    if price_val is None:
        price_val = first_var.get("price", 0.0)
    
    source_price_usd = float(price_val)
    if source_price_usd > 500:  # Likely in cents (e.g. 9900)
        source_price_usd /= 100.0

    compare_val = raw_data.get("compare_at_price")
    if compare_val is None:
        compare_val = first_var.get("compare_at_price")
    
    source_compare_usd = None
    if compare_val is not None:
        source_compare_usd = float(compare_val)
        if source_compare_usd > 500:
            source_compare_usd /= 100.0

    # Currency conversion
    price_inr = convert_usd_to_inr(source_price_usd, usd_to_inr_rate)
    compare_inr = convert_usd_to_inr(source_compare_usd, usd_to_inr_rate) if source_compare_usd else None

    # 3. Stock & Availability
    is_available = raw_data.get("available")
    if is_available is None:
        is_available = first_var.get("available", True)
    availability = "in_stock" if is_available else "out_of_stock"

    # 4. Images
    images = clean_images(raw_data)
    featured_image = images[0] if images else None

    # 5. Extraction of Color & SKU
    color_name = extract_color_from_title(title)
    sku = first_var.get("sku") or f"JW-{handle.upper()[:10]}"

    # 6. Specifications & Material Extraction from body_html
    body_html = raw_data.get("body_html") or raw_data.get("description") or ""
    specs = parse_specifications(body_html)
    material = specs.get("Material") or specs.get("Major Material") or specs.get("Main Material") or "Vegan Leather"

    # 7. Generate Rich Description HTML with Size Guide Accordion
    description_html = generate_description_html(body_html, specs)

    # 8. Canonical Variants Array
    variants = [
        {
            "id": first_var.get("id"),
            "sku": sku,
            "title": color_name or "Default Title",
            "price": f"{price_inr:.2f}",
            "compare_at_price": f"{compare_inr:.2f}" if compare_inr and compare_inr > price_inr else None,
            "source_price": source_price_usd,
            "source_compare_at_price": source_compare_usd,
            "currency": "INR",
            "source_currency": "USD",
            "in_stock": is_available,
            "image_url": featured_image,
            "option_values": [
                {"option_name": "Color", "name": color_name or "Standard"}
            ]
        }
    ]

    # 9. Product Options
    product_options = [
        {
            "name": "Color",
            "values": [{"name": color_name or "Standard"}]
        }
    ]

    tags = raw_data.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    return {
        "source_store": "jwpei",
        "source_url": f"https://www.jwpei.com/products/{handle}",
        "handle": handle,
        "title": title,
        "vendor": vendor,
        "product_type": product_type,
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
        "tags": tags[:20],  # Keep clean top tags
        "groups": [group_name]
    }


def clean_title(title: str) -> str:
    """Sanitize title string."""
    cleaned = html.unescape(title)
    cleaned = cleaned.replace("", "").strip()
    return cleaned


def extract_color_from_title(title: str) -> str:
    """Extract color suffix from product title (e.g., 'Thea Top Handle Bag - Dark Olive' -> 'Dark Olive')."""
    if " - " in title:
        parts = title.split(" - ")
        return parts[-1].strip()
    return "Standard"


def clean_images(raw_data: Dict[str, Any]) -> List[str]:
    """Extract and clean high-resolution image URLs."""
    urls = []
    raw_images = raw_data.get("images", [])
    for img in raw_images:
        src = ""
        if isinstance(img, dict):
            src = img.get("src", "")
        elif isinstance(img, str):
            src = img
        if src.startswith("//"):
            src = f"https:{src}"
        if src.startswith("http"):
            # Strip width constraints to preserve high resolution
            src = re.sub(r'&width=\d+', '', src)
            if src not in urls:
                urls.append(src)
    return urls


def parse_specifications(body_html: str) -> Dict[str, str]:
    """Parse key-value specifications from JW PEI HTML description."""
    specs = {}
    clean_text = html.unescape(body_html)
    clean_text = clean_text.replace("&nbsp;", " ").replace("\xa0", " ")
    
    # 1. Match <li ...>(.*?)</li> patterns
    li_matches = re.findall(r'<li[^>]*>(.*?)</li>', clean_text, re.DOTALL | re.IGNORECASE)
    for li in li_matches:
        plain_li = re.sub(r'<[^>]+>', ' ', li)
        plain_li = re.sub(r'\s+', ' ', plain_li).strip()
        if not plain_li:
            continue
        if ":" in plain_li:
            key, val = plain_li.split(":", 1)
            key = key.strip()
            val = re.sub(r'\s+"', '"', val.strip())
            specs[key] = val
            if key in ("Dimension", "Dimensions", "Bag Dimension"):
                specs["Bag Dimensions"] = val
            elif key in ("Main Material", "Major Material"):
                specs["Material"] = val
        elif "hardware" in plain_li.lower():
            specs["Hardware"] = plain_li.strip()
        elif "crossbody" in plain_li.lower() or "shoulder" in plain_li.lower() or "hand" in plain_li.lower():
            specs["Carrying Style"] = plain_li.strip()
        elif "pocket" in plain_li.lower() or "compartment" in plain_li.lower():
            specs["Pockets"] = plain_li.strip()
        elif "fits for" in plain_li.lower() or "phone" in plain_li.lower():
            specs["Capacity"] = plain_li.strip()
        elif "strap" in plain_li.lower():
            specs["Strap"] = plain_li.strip()
        elif "x" in plain_li.lower() and ('"' in plain_li or "cm" in plain_li):
            specs["Bag Dimensions"] = plain_li.strip()

    # 2. Line-by-line fallback if no li matches
    if not specs:
        lines = [line.strip() for line in re.sub(r'<[^>]+>', '\n', clean_text).splitlines() if line.strip()]
        for line in lines:
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip()
                val = re.sub(r'\s+"', '"', val.strip())
                specs[key] = val
                if key in ("Dimension", "Dimensions", "Bag Dimension"):
                    specs["Bag Dimensions"] = val
                elif key in ("Main Material", "Major Material"):
                    specs["Material"] = val
            elif "x" in line.lower() and ('"' in line or "cm" in line):
                specs["Bag Dimensions"] = line

    return specs


def generate_description_html(body_html: str, specs: Dict[str, str]) -> str:
    """
    Format clean HTML body with an integrated Size & Dimensions accordion.
    100% compatible with all Shopify themes.
    """
    # Extract leading marketing paragraph if present
    p_match = re.search(r'<p>(.*?)</p>', body_html, re.DOTALL | re.IGNORECASE)
    lead_paragraph = ""
    if p_match:
        lead_paragraph = re.sub(r'<[^>]+>', '', p_match.group(1)).replace("", "").strip()

    dims = specs.get("Bag Dimensions") or specs.get("Dimension") or specs.get("Dimensions") or "N/A"
    handle_drop = specs.get("Handle Drop", "N/A")
    strap_drop = specs.get("Shoulder Strap Drop", "N/A")
    hardware = specs.get("Hardware", "N/A")
    lining = specs.get("Lining Material", specs.get("Lining", "N/A"))
    material = specs.get("Material") or specs.get("Major Material") or specs.get("Main Material") or "Vegan Leather"

    out_html = f"""<div class="product-description">
  <p class="product-summary">{html.escape(lead_paragraph)}</p>
  
  <div class="product-highlights">
    <h4>Product Specifications</h4>
    <ul>
      <li><strong>Material:</strong> {html.escape(material)}</li>
      <li><strong>Lining:</strong> {html.escape(lining)}</li>
      <li><strong>Hardware Finish:</strong> {html.escape(hardware)}</li>
    </ul>
  </div>

  <details class="size-guide-accordion" style="margin-top: 15px; border: 1px solid #e5e5e5; border-radius: 6px; padding: 10px;">
    <summary style="font-weight: bold; cursor: pointer;">📏 Size & Measurement Guide</summary>
    <table style="width: 100%; margin-top: 10px; border-collapse: collapse; font-size: 14px;">
      <tbody>
        <tr style="border-bottom: 1px solid #f0f0f0;">
          <td style="padding: 6px; font-weight: 600;">Bag Dimensions</td>
          <td style="padding: 6px;">{html.escape(dims)}</td>
        </tr>
        <tr style="border-bottom: 1px solid #f0f0f0;">
          <td style="padding: 6px; font-weight: 600;">Handle Drop</td>
          <td style="padding: 6px;">{html.escape(handle_drop)}</td>
        </tr>
        <tr>
          <td style="padding: 6px; font-weight: 600;">Shoulder Strap Drop</td>
          <td style="padding: 6px;">{html.escape(strap_drop)}</td>
        </tr>
      </tbody>
    </table>
  </details>
</div>"""
    return out_html
