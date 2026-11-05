"""
Store Inflow Normalizer: SEPHORA
Transforms raw Sephora Redux PDP data (from page.product JSON) into canonical dropship schema.
Pure functions only, zero classes (ADR 0004, ADR 0005, ADR 0006).
"""
import re
import html
import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple
from storage.forex import convert_usd_to_inr


def clean_text(val: Optional[str]) -> str:
    """Sanitize text strings, stripping HTML entities, replacement characters, and excess whitespace."""
    if not val:
        return ""
    text = html.unescape(str(val))
    replacements = {
        '\xa0': ' ',
        '\u2019': "'",
        '\u2018': "'",
        '\u201c': '"',
        '\u201d': '"',
        '\u2013': '-',
        '\u2014': '-',
        '\u2122': '™',
        '\xae': '®',
        '\ufffd': '',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def parse_price_str(price_val: Any) -> float:
    """Parse string or float price like '$25.00' into a float."""
    if price_val is None:
        return 0.0
    if isinstance(price_val, (int, float)):
        return float(price_val)
    # Strip currency signs and commas
    cleaned = re.sub(r'[^\d.]', '', str(price_val))
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0


def clean_image_url(url: Optional[str]) -> Optional[str]:
    """Clean image URL by stripping resizing/query params while preserving base path."""
    if not url:
        return None
    url = url.split("?")[0].strip()
    if url.startswith("//"):
        url = "https:" + url
    elif url.startswith("/"):
        url = "https://www.sephora.com" + url
    return url


def build_accordions_html(
    description_raw: str,
    suggested_usage: Optional[str],
    ingredients: Optional[str],
    highlights: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Build rich description HTML with collapsible accordions for Suggested Usage & Ingredients.
    Adheres to ADR 0006 for unified UI layout.
    """
    parts = []

    # Highlights Badges (Clean, Vegan, Cruelty-Free, etc.)
    if highlights:
        badge_spans = []
        for h in highlights:
            name = clean_text(h.get("name") or h.get("altText"))
            if name and len(name) < 40:
                badge_spans.append(
                    f'<span style="display:inline-block;background:#f3f4f6;color:#1f2937;'
                    f'padding:3px 10px;border-radius:12px;font-size:12px;margin:2px 4px 2px 0;'
                    f'font-weight:500;">✓ {html.escape(name)}</span>'
                )
        if badge_spans:
            parts.append(f'<div class="product-highlights" style="margin-bottom:16px;">{"".join(badge_spans)}</div>')

    # Main Description
    if description_raw:
        clean_desc = description_raw.replace('\xa0', ' ').replace('\ufffd', '').replace('', '')
        parts.append(f'<div class="product-description-main" style="margin-bottom:20px;line-height:1.6;">{clean_desc}</div>')

    # Accordion: How to Use
    if suggested_usage and clean_text(suggested_usage):
        usage_clean = suggested_usage.replace('\xa0', ' ').replace('\ufffd', '').replace('', '')
        parts.append(
            '<details class="size-guide-accordion" style="margin-top:16px;border-top:1px solid #e5e7eb;padding-top:12px;">'
            '<summary style="font-weight:600;font-size:15px;cursor:pointer;padding:6px 0;outline:none;'
            'display:flex;justify-content:space-between;align-items:center;">'
            '<span>How to Use</span>'
            '<span style="font-size:18px;color:#6b7280;">+</span>'
            '</summary>'
            f'<div style="padding:12px 0 6px 0;line-height:1.6;color:#374151;">{usage_clean}</div>'
            '</details>'
        )

    # Accordion: Ingredients
    if ingredients and clean_text(ingredients):
        ing_clean = ingredients.replace('\xa0', ' ').replace('\ufffd', '').replace('', '')
        parts.append(
            '<details class="size-guide-accordion" style="margin-top:12px;border-top:1px solid #e5e7eb;'
            'border-bottom:1px solid #e5e7eb;padding:12px 0;">'
            '<summary style="font-weight:600;font-size:15px;cursor:pointer;padding:6px 0;outline:none;'
            'display:flex;justify-content:space-between;align-items:center;">'
            '<span>Ingredients</span>'
            '<span style="font-size:18px;color:#6b7280;">+</span>'
            '</summary>'
            f'<div style="padding:12px 0 6px 0;line-height:1.6;color:#374151;font-size:13px;">{ing_clean}</div>'
            '</details>'
        )

    return "\n".join(parts)


def parse_sephora_payload(
    raw_pdp_json: Dict[str, Any],
    usd_to_inr_rate: float,
    default_brand: str = "",
    source_url: str = ""
) -> Dict[str, Any]:
    """
    Transforms raw Sephora page.product JSON into canonical dropship schema.
    Extracts all regularChildSkus into granular variants.
    Computes whole-rupee INR prices (0 paise).
    Builds ingredient and how-to-use HTML accordions.
    """
    pdetails = raw_pdp_json.get("productDetails") or {}
    current_sku = raw_pdp_json.get("currentSku") or {}
    child_skus = raw_pdp_json.get("regularChildSkus") or []

    # 1. Identity & Handle
    raw_title = pdetails.get("displayName") or raw_pdp_json.get("displayName") or ""
    title = clean_text(raw_title)

    brand_obj = pdetails.get("brand") or raw_pdp_json.get("brand") or {}
    brand_name = clean_text(brand_obj.get("displayName")) if isinstance(brand_obj, dict) else clean_text(str(brand_obj))
    if not brand_name:
        brand_name = default_brand or "Sephora"

    product_id = raw_pdp_json.get("productId") or pdetails.get("productId") or ""
    
    # Handle / Slug
    handle_base = f"{brand_name} {title}".lower()
    handle = re.sub(r'[^a-z0-9\-]+', '-', handle_base).strip('-')
    if product_id:
        handle = f"{handle}-{product_id.lower()}"

    # Category & Product Type
    cat_obj = raw_pdp_json.get("parentCategory") or {}
    product_type = clean_text(cat_obj.get("displayName") or "Beauty")
    category_chain = []
    curr_cat = cat_obj
    while isinstance(curr_cat, dict) and curr_cat.get("displayName"):
        category_chain.append(clean_text(curr_cat.get("displayName")))
        curr_cat = curr_cat.get("parentCategory")

    # 2. Base SKU & Canonical URL
    if not source_url:
        target_path = raw_pdp_json.get("targetUrl") or raw_pdp_json.get("seoCanonicalUrl") or ""
        source_url = "https://www.sephora.com" + target_path if target_path.startswith("/") else target_path

    # 3. Base Pricing
    source_price_usd = parse_price_str(current_sku.get("listPrice"))
    if source_price_usd <= 0 and child_skus:
        source_price_usd = parse_price_str(child_skus[0].get("listPrice"))
    
    # Whole-rupee INR pricing math (ADR 0006)
    price_inr = int(round(convert_usd_to_inr(source_price_usd, usd_to_inr_rate)))
    compare_inr = None  # Sephora regular catalog items list regular listPrice

    # 4. Variants Matrix Extraction
    variants = []
    images_set = []
    seen_image_urls = set()

    # If regularChildSkus has variants, process them; else fallback to currentSku
    sku_list = child_skus if child_skus else ([current_sku] if current_sku else [])

    for sk in sku_list:
        sk_id = str(sk.get("skuId", "")).strip()
        if not sk_id:
            continue

        sk_val = clean_text(sk.get("variationValue") or sk.get("variationDesc") or sk.get("displayName"))
        sk_type = clean_text(sk.get("variationTypeDisplayName") or sk.get("variationType") or "Option")
        sk_size = clean_text(sk.get("size"))
        
        # Build human-readable variant title
        if sk_val and sk_size and sk_val.lower() != sk_size.lower():
            v_title = f"{sk_val} - {sk_size}"
        elif sk_val:
            v_title = sk_val
        elif sk_size:
            v_title = sk_size
        else:
            v_title = "Standard"

        # Pricing
        sk_price_usd = parse_price_str(sk.get("listPrice"))
        if sk_price_usd <= 0:
            sk_price_usd = source_price_usd
        sk_price_inr = int(round(convert_usd_to_inr(sk_price_usd, usd_to_inr_rate)))

        # Live Stock Truth (ADR 0005)
        # Sephora gives isOutOfStock: True/False explicitly on each sku
        is_oos = bool(sk.get("isOutOfStock", False))
        is_in_stock = not is_oos

        # 1-to-1 Image Binding
        img_dict = sk.get("skuImages") or {}
        img_url = clean_image_url(img_dict.get("imageUrl") or img_dict.get("image450") or img_dict.get("image250"))
        if not img_url:
            img_url = f"https://www.sephora.com/productimages/sku/s{sk_id}-main-zoom.jpg"

        # Swatch URL
        swatch_url = clean_image_url(sk.get("smallImage"))
        if not swatch_url:
            swatch_url = f"https://www.sephora.com/productimages/sku/s{sk_id}-swatch-zoom.jpg"

        if img_url and img_url not in seen_image_urls:
            images_set.append(img_url)
            seen_image_urls.add(img_url)

        # Collect alternate images for this variant
        for alt_img in sk.get("alternateImages", []):
            alt_u = clean_image_url(alt_img.get("imageUrl") or alt_img.get("image250"))
            if alt_u and alt_u not in seen_image_urls:
                images_set.append(alt_u)
                seen_image_urls.add(alt_u)

        v_record = {
            "id": sk_id,
            "sku": sk_id,
            "title": v_title,
            "option1": v_title,
            "option2": sk_size if (sk_size and sk_val and sk_size != sk_val) else None,
            "price": sk_price_inr,
            "source_price": sk_price_usd,
            "source_price_usd": sk_price_usd,
            "current_price": sk_price_inr,
            "price_inr": sk_price_inr,
            "compare_at_price": None,
            "in_stock": is_in_stock,
            "is_active": is_in_stock,
            "barcode": sk_id,
            "image_url": img_url,
            "swatch_url": swatch_url,
            "size": sk_size,
            "variation_value": sk_val,
            "variation_type": sk_type
        }
        variants.append(v_record)

    # 5. Stock Harmony Invariant (Non-Negotiable)
    # If >= 1 variant is in stock, parent is in_stock; if all OOS, parent is out_of_stock
    has_in_stock = any(v["in_stock"] for v in variants)
    availability = "in_stock" if has_in_stock else "out_of_stock"
    is_active = has_in_stock

    # 6. Primary Image
    primary_image = images_set[0] if images_set else f"https://www.sephora.com/productimages/sku/s{current_sku.get('skuId')}-main-zoom.jpg"

    # 7. Rich Accordions Description
    short_desc = pdetails.get("shortDescription") or ""
    long_desc = pdetails.get("longDescription") or ""
    desc_raw = short_desc or long_desc or pdetails.get("imageAltText") or ""
    
    suggested_usage = pdetails.get("suggestedUsage") or ""
    
    # Ingredient description from current SKU or first child
    ingredient_desc = current_sku.get("ingredientDesc") or ""
    if not ingredient_desc and child_skus:
        for ch in child_skus:
            if ch.get("ingredientDesc"):
                ingredient_desc = ch.get("ingredientDesc")
                break

    highlights = current_sku.get("highlights") or []
    description_html = build_accordions_html(
        description_raw=desc_raw,
        suggested_usage=suggested_usage,
        ingredients=ingredient_desc,
        highlights=highlights
    )

    # 8. Specifications / Refinements
    specs = {}
    if product_type:
        specs["Category"] = product_type
    if category_chain:
        specs["Breadcrumbs"] = " > ".join(category_chain)
    
    for ref in current_sku.get("skuRefinements", []):
        k = clean_text(ref.get("key"))
        vals = [clean_text(v) for v in ref.get("values", []) if v]
        if k and vals:
            specs[k] = ", ".join(vals)

    # 9. Tags
    tags = [brand_name, product_type, "Beauty", "Sephora", "Cosmetics"]
    for cat in category_chain:
        if cat not in tags:
            tags.append(cat)
    for h in highlights:
        h_name = clean_text(h.get("name") or h.get("altText"))
        if h_name and h_name not in tags and len(h_name) < 30:
            tags.append(h_name)

    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    return {
        "source_store": "sephora",
        "source_url": source_url,
        "handle": handle,
        "title": title,
        "vendor": brand_name,
        "brand": brand_name,
        "product_type": product_type,
        "gender": "Unisex",
        "source_sku": product_id or (current_sku.get("skuId") or "SEPHORA-UNKNOWN"),
        "source_price": source_price_usd,
        "source_price_usd": source_price_usd,
        "source_compare_at_price": None,
        "current_price": price_inr,
        "current_price_inr": price_inr,
        "compare_at_price": compare_inr,
        "currency": "INR",
        "source_currency": "USD",
        "forex_rate_used": usd_to_inr_rate,
        "availability": availability,
        "is_active": is_active,
        "primary_image_url": primary_image,
        "images": images_set[:25],
        "specifications": specs,
        "descriptionHtml": description_html,
        "description_html": description_html,
        "variants": variants,
        "product_options": [
            {
                "name": current_sku.get("variationTypeDisplayName") or current_sku.get("variationType") or "Option",
                "values": [v["title"] for v in variants]
            }
        ],
        "tags": tags[:25],
        "groups": ["beauty", brand_name.lower().replace(" ", "-")],
        "created_at": now_iso,
        "last_verified_at": now_iso
    }
