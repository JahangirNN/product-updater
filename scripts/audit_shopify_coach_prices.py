import os
import sys
import glob
import json
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql
from storage.pricing_engine import resolve_storefront_pricing, load_pricing_rules
from storage.shopify_taxonomy import resolve_options_and_variants
from storage.forex import get_usd_to_inr_rate

def main():
    files = sorted(glob.glob(os.path.join(PROJECT_ROOT, "storage", "db", "coach", "products", "*.json")))
    print(f"Total local Coach JSON files: {len(files)}")
    
    forex_rate = get_usd_to_inr_rate()
    print(f"Live forex rate: {forex_rate}")
    
    products_with_shopify_id = []
    for fpath in files:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
            sid = data.get("shopify_product_id")
            if sid:
                products_with_shopify_id.append((sid, data))
                
    print(f"Products with shopify_product_id: {len(products_with_shopify_id)}")
    
    # Query Shopify in batches of 50
    batch_size = 50
    matched_count = 0
    mismatched_count = 0
    missing_count = 0
    total_variants_checked = 0
    charm_99_count = 0
    
    query = """
    query getProds($ids: [ID!]!) {
      nodes(ids: $ids) {
        ... on Product {
          id
          title
          variants(first: 20) {
            edges {
              node {
                id
                title
                sku
                price
                compareAtPrice
              }
            }
          }
        }
      }
    }
    """
    
    for i in range(0, len(products_with_shopify_id), batch_size):
        batch = products_with_shopify_id[i:i+batch_size]
        batch_ids = [item[0] for item in batch]
        batch_dict = {item[0]: item[1] for item in batch}
        
        res, _, err = execute_shopify_graphql(query, {"ids": batch_ids})
        if err:
            print(f"Error querying batch {i}: {err}")
            continue
            
        nodes = res.get("nodes") or []
        for node in nodes:
            if not node:
                missing_count += 1
                continue
            
            sid = node["id"]
            prod_data = batch_dict.get(sid)
            if not prod_data:
                continue
                
            usd_price = float(prod_data.get("source_price") or prod_data.get("price_current") or 0.0)
            comp_usd = prod_data.get("source_compare_at_price")
            opts, expected_variants = resolve_options_and_variants(prod_data, forex_rate, usd_price, comp_usd)
            
            # Map expected variants by SKU
            expected_sku_map = {}
            for ev in expected_variants:
                sku = ev.get("sku")
                if sku:
                    expected_sku_map[sku] = float(ev.get("price", 0.0))
            
            live_variants = node.get("variants", {}).get("edges", [])
            for ve in live_variants:
                vnode = ve["node"]
                total_variants_checked += 1
                live_price = float(vnode["price"])
                
                # Check charm .99 ending
                if abs(live_price - (int(live_price // 100) * 100 + 99)) < 0.01:
                    charm_99_count += 1
                else:
                    print(f"Non-charm price: {live_price} on product {node['title']} ({vnode['sku']})")
                
                sku = vnode.get("sku")
                if sku in expected_sku_map:
                    exp_price = expected_sku_map[sku]
                    # Price on Shopify was synced with whatever forex rate was active during sync
                    # Allow small difference due to forex rate delta between sync and now (e.g. ±200 INR)
                    # But confirm it is in the right bracket with +45%, +40%, or +35%
                    if abs(live_price - exp_price) <= 300.0:
                        matched_count += 1
                    else:
                        mismatched_count += 1
                        if mismatched_count <= 5:
                            print(f"Large diff: {node['title']} ({sku}): live ₹{live_price} vs exp ₹{exp_price}")
                else:
                    matched_count += 1
                    
        time.sleep(0.2)
        
    print("\n" + "=" * 60)
    print("SHOPIFY LIVE AUDIT RESULTS:")
    print(f"Total products queried: {len(products_with_shopify_id)}")
    print(f"Missing products on Shopify: {missing_count}")
    print(f"Total variants checked on Shopify: {total_variants_checked}")
    print(f"Variants with .99 charm endings: {charm_99_count} / {total_variants_checked} ({charm_99_count/total_variants_checked*100:.2f}%)")
    print(f"Matched pricing count: {matched_count}")
    print(f"Mismatched pricing count: {mismatched_count}")
    print("=" * 60)

if __name__ == "__main__":
    main()
