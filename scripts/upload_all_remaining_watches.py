"""
All Remaining Watches Ingestion Engine
Ingests all remaining 372 luxury and designer watches (Citizen, Movado, Seiko, Michael Kors, Ferragamo)
into Shopify Admin GraphQL, completing 100% of the entire 575 watch catalog.
Adheres to ADR 0005, 0006, 0015, 0019, and 0020.
"""
import sys
import os
import glob
import json
import time
import re
from typing import Dict, Any, List, Tuple

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


def detect_gender(prod: Dict[str, Any]) -> str:
    """Detect gender cleanly as Men, Women, or Unisex."""
    raw_g = str(prod.get("gender") or (prod.get("specifications") or {}).get("Gender") or "").lower()
    title = str(prod.get("title", "")).lower()
    text = f"{raw_g} {title}"
    
    if re.search(r"\b(women|womens|women\'s|ladies|lady)\b", text):
        return "Women"
    elif re.search(r"\bunisex\b", text):
        return "Unisex"
    elif re.search(r"\b(men|mens|men\'s)\b", text):
        return "Men"
    return "Men"


def prepare_watch_payload(prod: Dict[str, Any], forex_rate: float) -> Dict[str, Any]:
    title = prod.get("title", "")
    vendor = prod.get("vendor") or prod.get("brand", "Luxury")
    product_type = "Watches"
    handle = prod.get("handle")
    desc_html = prod.get("descriptionHtml") or prod.get("description_html") or ""
    
    # 1. Whole-rupee INR pricing
    source_price = float(prod.get("source_price") or prod.get("price_current") or 0.0)
    inr_price = float(round(source_price * forex_rate))
    price_str = f"{inr_price:.2f}"
    
    compare_source = prod.get("source_compare_at_price") or prod.get("compare_at_price_source")
    compare_str = None
    if compare_source and float(compare_source) > source_price:
        inr_comp = float(round(float(compare_source) * forex_rate))
        compare_str = f"{inr_comp:.2f}"
        
    # 2. Luxury Consumer Taxonomy Tags
    tags = list(prod.get("tags", []))
    for t in ["Luxury Watches", "Watches", f"Brand:{vendor}", vendor]:
        if t not in tags:
            tags.append(t)
            
    gender = detect_gender(prod)
    if gender == "Men":
        tags.extend(["Men's", "Gender:Men's", "Gender:Men"])
    elif gender == "Women":
        tags.extend(["Women's", "Gender:Women's", "Gender:Women", "Ladies"])
    else:
        tags.extend(["Unisex", "Gender:Unisex", "Men's", "Women's"])
        
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
    
    # 4. Images (up to 6 CDN images)
    media_files = []
    for img_url in prod.get("images", [])[:6]:
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


def upload_all_remaining_watches():
    print("=" * 75)
    print("BATCH INGESTION: ALL REMAINING WATCHES ACROSS ALL STORES")
    print("=" * 75)
    
    db_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "db")
    all_files = glob.glob(os.path.join(db_root, "*", "products", "*.json"))
    
    pending_watches: List[Tuple[str, Dict[str, Any]]] = []
    already_uploaded = 0
    
    for fpath in all_files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                p = json.load(f)
            pt = str(p.get("product_type", "")).lower()
            store = p.get("source_store") or p.get("store") or ""
            
            if pt == "watches" or store == "jomashop":
                if p.get("shopify_product_id"):
                    already_uploaded += 1
                else:
                    pending_watches.append((fpath, p))
        except Exception as e:
            pass
            
    print(f"[*] Total Watches in DB:       {len(pending_watches) + already_uploaded}")
    print(f"[*] Already Synced on Shopify: {already_uploaded}")
    print(f"[*] Pending Upload Batch:      {len(pending_watches)}")
    
    if not pending_watches:
        print("[+] All watches are already 100% synced to Shopify!")
        return
        
    forex_rate = get_usd_to_inr_rate()
    print(f"[*] Active Forex Rate:         1 USD = INR {forex_rate:.2f}\n")
    
    success_count = 0
    fail_count = 0
    start_time = time.time()
    
    for idx, (fpath, prod) in enumerate(pending_watches, 1):
        title = prod.get("title", "Unknown")
        vendor = prod.get("vendor") or prod.get("brand") or "Luxury"
        source_price = prod.get("source_price", 0)
        
        print(f"[{idx:03d}/{len(pending_watches)}] [{vendor:12s}] {title[:42]} (${source_price} USD)...", end=" ", flush=True)
        
        input_payload = prepare_watch_payload(prod, forex_rate)
        
        data, ext, err = execute_shopify_graphql(
            PRODUCT_SET_MUTATION,
            variables={"input": input_payload, "synchronous": True}
        )
        
        if err or not data:
            print(f"[FAIL GraphQL: {err}]")
            fail_count += 1
            time.sleep(1.0)
            continue
            
        res = data.get("productSet", {})
        u_errors = res.get("userErrors", [])
        if u_errors:
            print(f"[FAIL UserErrors: {u_errors}]")
            fail_count += 1
            time.sleep(1.0)
            continue
            
        p_node = res.get("product", {})
        shopify_gid = p_node.get("id")
        created_handle = p_node.get("handle")
        
        # Stamp back to local JSON file
        prod["shopify_product_id"] = shopify_gid
        prod["shopify_handle"] = created_handle
        prod["shopify_synced_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        prod["shopify_sync_pending"] = False
        
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(prod, f, indent=2)
            
        success_count += 1
        print(f"[OK -> GID: {shopify_gid}]")
        time.sleep(0.3)  # polite pacing for GraphQL Admin API rate limit
        
    elapsed = time.time() - start_time
    print("\n" + "=" * 75)
    print(f"WATCH INGESTION COMPLETE: {success_count}/{len(pending_watches)} Succeeded ({fail_count} Failed) in {elapsed:.1f}s.")
    print("=" * 75)
    
    # Rebuild index
    print("[*] Rebuilding centralized storage index...")
    build_and_save_index()
    print("[*] Storage index successfully updated.")


if __name__ == "__main__":
    upload_all_remaining_watches()
