import os
import sys
import glob
import json
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_sync import upsert_product_to_shopify
from storage.forex import get_usd_to_inr_rate
from storage.shopify_auth import execute_shopify_graphql

target_handles = [
    "hana-large-tote-bag-pink",
    "celeste-woven-textured-envelope-top-handle-bag-dark-brown",
    "ellie-metal-ring-embellished-top-handle-bag-lemon-yellow",
    "mini-rowan-crossbody-bag",
    "nolita-19-in-signature-canvas",
    "nell-fringe-hardware-top-handle-bag-burgundy"
]

forex_rate = get_usd_to_inr_rate()
print(f"Using forex rate: {forex_rate}")

for handle in target_handles:
    print(f"\nSearching local json for handle: {handle}...")
    found_file = None
    found_data = None
    for store in ["jwpei", "coach", "michaelkors"]:
        pattern = os.path.join(PROJECT_ROOT, "storage", "db", store, "products", "*.json")
        for f in glob.glob(pattern):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    d = json.load(fp)
            except Exception:
                continue
            if d.get("handle") == handle or d.get("shopify_handle") == handle:
                found_file = f
                found_data = d
                break
        if found_file:
            break

    if not found_file:
        print(f"ERROR: Local json not found for {handle}!")
        continue

    print(f"Found file: {found_file} (Variants: {len(found_data.get('variants', []))})")
    
    # Run upsert
    ok, p_node, err = upsert_product_to_shopify(found_data, forex_rate)
    print(f"Upsert result: ok={ok}, err={err}")

print("\nWaiting 10 seconds for Shopify CDN to attach variant images & inventory...")
time.sleep(10)

# Check Shopify GraphQL variant images & inventoryItem
q = """
query checkVariants($handle: String!) {
  productByHandle(handle: $handle) {
    id
    title
    handle
    variants(first: 30) {
      nodes {
        id
        title
        availableForSale
        inventoryPolicy
        inventoryItem {
          tracked
        }
        image { id url }
      }
    }
  }
}
"""

for handle in target_handles:
    res, ext, err = execute_shopify_graphql(q, variables={"handle": handle})
    p = res.get("productByHandle") if res else None
    if p:
        var_nodes = p.get("variants", {}).get("nodes", [])
        with_imgs = sum(1 for v in var_nodes if v.get("image"))
        with_avail = sum(1 for v in var_nodes if v.get("availableForSale"))
        print(f"\n[{p['handle']}] Variants: {len(var_nodes)} | With images: {with_imgs}/{len(var_nodes)} | Available for sale: {with_avail}/{len(var_nodes)}")
        for v in var_nodes[:2]:
            print(f"   {v['title']} -> Img: {bool(v.get('image'))} | Avail: {v.get('availableForSale')} | Policy: {v.get('inventoryPolicy')} | Tracked: {v.get('inventoryItem', {}).get('tracked')}")
