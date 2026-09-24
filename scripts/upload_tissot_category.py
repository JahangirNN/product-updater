"""
Tissot Luxury Watches Category Ingestion Script
Systematically ingests all 157 Tissot luxury watches to Shopify Admin GraphQL.
Adheres to ADR 0005, 0006, 0015, 0019, and 0020.
"""
import sys
import os
import glob
import json
import time
from typing import Dict, Any, List

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.shopify_auth import execute_shopify_graphql
from storage.forex import get_usd_to_inr_rate
from storage.db import build_and_save_index

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

def prepare_tissot_payload(prod: Dict[str, Any], forex_rate: float) -> Dict[str, Any]:
    title = prod.get("title", "")
    vendor = "Tissot"
    product_type = "Watches"
    handle = prod.get("handle")
    desc_html = prod.get("descriptionHtml", "")
    
    # 1. Whole-rupee INR pricing
    source_price = float(prod.get("source_price") or 0.0)
    inr_price = float(round(source_price * forex_rate))
    price_str = f"{inr_price:.2f}"
    
    compare_source = prod.get("source_compare_at_price")
    compare_str = None
    if compare_source and float(compare_source) > source_price:
        inr_comp = float(round(float(compare_source) * forex_rate))
        compare_str = f"{inr_comp:.2f}"
        
    # 2. Tags
    tags = list(prod.get("tags", []))
    for t in ["Brand:Tissot", "Watches", "Luxury Watches"]:
        if t not in tags:
            tags.append(t)
            
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
    
    # 3. Sizing / Option (Case Diameter)
    variants_raw = prod.get("variants", [])
    case_diameter = "40 mm"
    if variants_raw and isinstance(variants_raw[0], dict):
        opt_vals = variants_raw[0].get("option_values", [])
        for opt in opt_vals:
            if opt.get("option_name") in ("Case Diameter", "Size"):
                case_diameter = opt.get("name", "40 mm")
                break
                
    source_sku = prod.get("source_sku") or prod.get("id") or ""
    sku_val = f"RARE-{source_sku}" if not source_sku.startswith("RARE-") else source_sku
    
    # 4. Images (up to 6)
    media_files = []
    for img_url in prod.get("images", [])[:6]:
        if img_url and isinstance(img_url, str) and img_url.startswith("http"):
            media_files.append({
                "originalSource": img_url,
                "contentType": "IMAGE"
            })
            
    is_in_stock = (prod.get("availability") == "in_stock")
    
    # 5. ProductSet Input
    payload = {
        "title": title,
        "vendor": vendor,
        "productType": product_type,
        "descriptionHtml": desc_html,
        "tags": tags,
        "status": "ACTIVE" if is_in_stock else "DRAFT",
        "productOptions": [
            {
                "name": "Case Diameter",
                "values": [{"name": case_diameter}]
            }
        ],
        "variants": [
            {
                "optionValues": [
                    {
                        "optionName": "Case Diameter",
                        "name": case_diameter
                    }
                ],
                "price": price_str,
                "compareAtPrice": compare_str,
                "sku": sku_val,
                "inventoryPolicy": "DENY"
            }
        ],
        "files": media_files
    }
    
    if prod.get("shopify_product_id"):
        payload["id"] = prod["shopify_product_id"]
    elif handle:
        payload["handle"] = handle
        
    return payload


def upload_tissot_category():
    print("=" * 75)
    print("UPLOADING TISSOT LUXURY WATCHES (157 PRODUCTS) TO THE RARE AVENUE")
    print("=" * 75)
    
    db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "db", "jomashop", "products")
    files = glob.glob(os.path.join(db_dir, "*.json"))
    
    tissot_files = []
    for fpath in files:
        with open(fpath, "r", encoding="utf-8") as f:
            p = json.load(f)
            if p.get("vendor") == "Tissot" or p.get("brand") == "Tissot":
                tissot_files.append((fpath, p))
                
    print(f"[*] Found {len(tissot_files)} Tissot luxury watches in local DB.")
    forex_rate = get_usd_to_inr_rate()
    print(f"[*] Active Forex: 1 USD = INR {forex_rate:.2f}\n")
    
    success_count = 0
    fail_count = 0
    
    for idx, (fpath, prod) in enumerate(tissot_files, 1):
        title = prod.get("title", "Unknown")
        source_price = prod.get("source_price", 0)
        
        print(f"[{idx:03d}/{len(tissot_files)}] Ingesting: {title[:48]} (${source_price} USD)...")
        
        input_payload = prepare_tissot_payload(prod, forex_rate)
        
        data, ext, err = execute_shopify_graphql(
            PRODUCT_SET_MUTATION,
            variables={"input": input_payload, "synchronous": True}
        )
        
        if err or not data:
            print(f"    [FAIL] GraphQL Error: {err}")
            fail_count += 1
            continue
            
        res = data.get("productSet", {})
        u_errors = res.get("userErrors", [])
        if u_errors:
            print(f"    [FAIL] UserErrors: {u_errors}")
            fail_count += 1
            continue
            
        p_node = res.get("product", {})
        shopify_gid = p_node.get("id")
        created_handle = p_node.get("handle")
        
        # Stamp back to local JSON
        prod["shopify_product_id"] = shopify_gid
        prod["shopify_handle"] = created_handle
        prod["shopify_synced_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        prod["shopify_sync_pending"] = False
        
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(prod, f, indent=2)
            
        success_count += 1
        print(f"    [SUCCESS] Ingested -> GID: {shopify_gid} (handle: {created_handle})")
        time.sleep(0.35)  # polite pacing for GraphQL rate limits
        
    print("\n" + "=" * 75)
    print(f"TISSOT INGESTION SUMMARY: {success_count}/{len(tissot_files)} Succeeded ({fail_count} Failed).")
    print("=" * 75)
    
    # Rebuild index
    print("[*] Rebuilding centralized storage index...")
    build_and_save_index()
    print("[*] Storage index successfully updated.")


if __name__ == "__main__":
    upload_tissot_category()
