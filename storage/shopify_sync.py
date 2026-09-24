"""
Shopify Catalog Ingestion & Real-Time Delta Synchronization Bridge
Pure functions for upserting products and pushing live price/stock delta shifts to Shopify Admin GraphQL.
Adheres to ADR 0005, 0006, 0015, 0019, and 0020.
"""
import os
import sys
import json
import time
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.shopify_auth import execute_shopify_graphql
from storage.forex import get_usd_to_inr_rate
from storage.logger import log_info, log_success, log_warning, log_error

PRODUCT_SET_MUTATION = """
mutation productSet($input: ProductSetInput!, $synchronous: Boolean!) {
  productSet(input: $input, synchronous: $synchronous) {
    product {
      id
      title
      handle
      status
      totalVariants
      onlineStoreUrl
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""


def prepare_product_set_payload(prod: Dict[str, Any], forex_rate: float) -> Dict[str, Any]:
    """
    Format a canonical product dictionary into a compliant ProductSetInput payload.
    Enforces authentic luxury brand vendor, whole-rupee INR pricing, options, and CDN media.
    """
    title = prod.get("title", "")
    vendor = prod.get("vendor") or prod.get("brand", "Rare")
    product_type = prod.get("product_type", "Luxury")
    handle = prod.get("handle")
    desc_html = prod.get("descriptionHtml", "")
    
    # 1. Whole-rupee INR pricing
    source_price = float(prod.get("source_price") or prod.get("price_current") or 0.0)
    inr_price = float(round(source_price * forex_rate))
    price_str = f"{inr_price:.2f}"
    
    compare_source = prod.get("source_compare_at_price")
    compare_str = None
    if compare_source and float(compare_source) > source_price:
        inr_comp = float(round(float(compare_source) * forex_rate))
        compare_str = f"{inr_comp:.2f}"
        
    # 2. Luxury Consumer Taxonomy Tags
    tags = list(prod.get("tags", []))
    if f"Brand:{vendor}" not in tags:
        tags.append(f"Brand:{vendor}")
    if product_type not in tags:
        tags.append(product_type)
        
    # Gender tag
    gender = prod.get("gender")
    if not gender:
        title_lower = title.lower()
        if "women" in title_lower or "ladies" in title_lower:
            gender = "Women"
        elif "unisex" in title_lower:
            gender = "Unisex"
        else:
            gender = "Men"
    tags.append(f"Gender:{gender}")
    tags = list(set(tags))
    
    # 3. Variants & Options
    variants_raw = prod.get("variants", [])
    option_name = "Size"
    option_values = []
    variant_inputs = []
    
    if variants_raw and isinstance(variants_raw, list) and len(variants_raw) > 0:
        first_var = variants_raw[0]
        # Detect option name from first variant option values
        if "option_values" in first_var and first_var["option_values"]:
            option_name = first_var["option_values"][0].get("option_name", "Size")
            
        for v in variants_raw:
            v_val = v.get("size") or v.get("title") or "Default"
            if "option_values" in v and v["option_values"]:
                v_val = v["option_values"][0].get("name", v_val)
            option_values.append(v_val)
            
            v_source_price = float(v.get("source_price") or source_price)
            v_inr_price = float(round(v_source_price * forex_rate))
            v_sku = v.get("sku") or prod.get("source_sku") or prod.get("id") or ""
            if not v_sku.startswith("RARE-"):
                v_sku = f"RARE-{v_sku}"
                
            v_compare_source = v.get("source_compare_at_price") or compare_source
            v_compare_str = None
            if v_compare_source and float(v_compare_source) > v_source_price:
                v_compare_str = f"{float(round(float(v_compare_source) * forex_rate)):.2f}"
                
            variant_inputs.append({
                "optionValues": [
                    {
                        "optionName": option_name,
                        "name": v_val
                    }
                ],
                "price": f"{v_inr_price:.2f}",
                "compareAtPrice": v_compare_str,
                "sku": v_sku,
                "inventoryPolicy": "DENY"
            })
    else:
        # Single default variant
        source_sku = prod.get("source_sku") or prod.get("id") or ""
        v_sku = f"RARE-{source_sku}" if not source_sku.startswith("RARE-") else source_sku
        option_values = ["Default"]
        variant_inputs = [{
            "optionValues": [{"optionName": "Title", "name": "Default Title"}],
            "price": price_str,
            "compareAtPrice": compare_str,
            "sku": v_sku,
            "inventoryPolicy": "DENY"
        }]
        option_name = "Title"

    # 4. Media Files (up to 8 CDN images)
    media_files = []
    for img_url in prod.get("images", [])[:8]:
        if img_url and isinstance(img_url, str) and img_url.startswith("http"):
            media_files.append({
                "originalSource": img_url,
                "contentType": "IMAGE"
            })
            
    is_in_stock = (prod.get("availability") == "in_stock")
    
    # 5. Construct ProductSetInput payload
    payload = {
        "title": title,
        "vendor": vendor,
        "productType": product_type,
        "descriptionHtml": desc_html,
        "tags": tags,
        "status": "ACTIVE" if is_in_stock else "DRAFT",
        "productOptions": [
            {
                "name": option_name,
                "values": [{"name": val} for val in set(option_values)]
            }
        ],
        "variants": variant_inputs
    }
    
    # If media files exist, attach them
    if media_files:
        payload["files"] = media_files
        
    if prod.get("shopify_product_id"):
        payload["id"] = prod["shopify_product_id"]
    elif handle:
        payload["handle"] = handle
        
    return payload


def upsert_product_to_shopify(prod: Dict[str, Any], forex_rate: Optional[float] = None) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Upsert a product to Shopify using the productSet GraphQL mutation.
    Returns (success, product_node, error_message).
    """
    if forex_rate is None:
        forex_rate = get_usd_to_inr_rate()
        
    payload = prepare_product_set_payload(prod, forex_rate)
    
    data, ext, err = execute_shopify_graphql(
        PRODUCT_SET_MUTATION,
        variables={"input": payload, "synchronous": True}
    )
    
    if err or not data:
        return False, None, f"GraphQL Error: {err}"
        
    res = data.get("productSet", {})
    u_errors = res.get("userErrors", [])
    if u_errors:
        err_details = "; ".join(f"{e.get('field')}: {e.get('message')}" for e in u_errors)
        return False, None, f"UserErrors: {err_details}"
        
    p_node = res.get("product")
    return True, p_node, ""


def sync_delta_to_shopify(updated_product: Dict[str, Any], delta_res: Dict[str, Any], forex_rate: Optional[float] = None) -> bool:
    """
    Instantly push price or stock shifts to Shopify for an already-linked product.
    Returns True if successfully synchronized.
    """
    shopify_id = updated_product.get("shopify_product_id")
    if not shopify_id:
        return False
        
    if forex_rate is None:
        forex_rate = get_usd_to_inr_rate()
        
    success, p_node, err = upsert_product_to_shopify(updated_product, forex_rate)
    if success:
        log_success(f"[SHOPIFY SYNC] Synced delta for {updated_product.get('title', '')[:35]} (GID: {shopify_id})")
        return True
    else:
        log_error(f"[SHOPIFY SYNC FAIL] Failed to sync delta for {updated_product.get('title', '')[:35]}: {err}")
        return False
