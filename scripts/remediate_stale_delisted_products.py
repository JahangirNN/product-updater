"""
Remediation Migration Script: Neutralize Stale/Retired JD Sports Products on Shopify
Neutralizes identified discontinued JD Sports products by setting them to DRAFT,
depleting all variant inventory to DENY, adding 'supplier-delisted', and stripping shipping tags.
Adheres to ADR 0005, 0006, 0015, 0021.
"""
import os
import sys
import json
import time
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.db import load_product, save_product, build_and_save_index
from storage.shopify_sync import upsert_product_to_shopify
from storage.shopify_auth import execute_shopify_graphql
from storage.logger import log_info, log_success, log_error, log_warning

TARGET_STALE_HANDLES = [
    "mens-nike-air-max-bia-casual-shoes-white-wolf-grey-black-3369755",
    "womens-nike-dunk-low-patent-leather-casual-shoes-pink-foam-black-white-3337873",
    "mens-nike-air-force-1-07-lv8-casual-shoes-wolf-grey-white-wolf-grey-3331631",
    "mens-nike-air-force-1-07-lv8-casual-shoes-black-iron-grey-light-smoke-grey-3331499",
    "mens-nike-dunk-low-retro-casual-shoes-white-deep-royal-pure-platinum-wolf-grey-3331871",
    "mens-nike-air-force-1-07-lv8-woven-casual-shoes-off-white-summit-white-off-white-3474404",
    "mens-nike-dunk-low-retro-casual-shoes-white-black-midnight-navy-3458563",
    "mens-nike-air-diamond-turf-2-casual-shoes-black-fire-red-metallic-gold-white-3385169"
]

GET_PRODUCT_QUERY = """
query getProductDetails($id: ID!) {
  product(id: $id) {
    id
    title
    handle
    status
    tags
    totalVariants
    variants(first: 20) {
      nodes {
        id
        sku
        inventoryPolicy
        inventoryItem {
          tracked
        }
      }
    }
  }
}
"""


def remediate_stale_jdsports_products() -> Dict[str, Any]:
    print("=" * 80)
    print("REMEDIATION: NEUTRALIZE STALE / RETIRED JD SPORTS CATALOG PRODUCTS")
    print("=" * 80)

    p_dir = os.path.join("storage", "db", "jdsports", "products")
    if not os.path.exists(p_dir):
        print(f"Directory {p_dir} does not exist.")
        return {"remediated": 0, "failed": 0}

    results = []
    remediated_count = 0
    failed_count = 0

    for fname in os.listdir(p_dir):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(p_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as pf:
                prod = json.load(pf)
        except Exception as e:
            continue

        handle = prod.get("handle")
        if handle not in TARGET_STALE_HANDLES:
            continue

        p_id = prod.get("id")
        title = prod.get("title", "")
        shopify_id = prod.get("shopify_product_id")

        print(f"\nProcessing target item: {handle}")
        print(f"  Title:      {title[:45]}")
        print(f"  Shopify ID: {shopify_id}")

        # 1. Neutralize in local database
        prod["delist_strikes"] = 2
        prod["supplier_delisted"] = True
        prod["availability"] = "out_of_stock"
        prod["is_active"] = False

        # Cascade all variants to in_stock = False
        for v in prod.get("variants", []):
            v["in_stock"] = False
            v["is_available"] = False

        # Operational tags
        curr_tags = set(prod.get("tags") or [])
        shipping_tags = {"ready to ship", "instant-ship", "manual-instant-ship-active"}
        curr_tags = {t for t in curr_tags if t.lower() not in shipping_tags}
        curr_tags.add("supplier-delisted")
        prod["tags"] = sorted(list(curr_tags))

        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        prod["last_verified_at"] = now_iso
        prod["updated_at"] = now_iso

        # Save to local database
        save_product(prod)
        print("  Local DB:   Marked delisted, strikes=2, variants depleted, 'supplier-delisted' tag added.")

        # 2. Push mutation to live Shopify
        if shopify_id:
            success, p_node, err = upsert_product_to_shopify(prod)
            if success:
                print(f"  Shopify:    Successfully pushed mutation. Status: {p_node.get('status')}")
                
                # 3. Query Shopify to verify
                verify_data, _, v_err = execute_shopify_graphql(GET_PRODUCT_QUERY, variables={"id": shopify_id})
                if verify_data and verify_data.get("product"):
                    node = verify_data["product"]
                    v_status = node.get("status")
                    v_tags = node.get("tags", [])
                    var_nodes = node.get("variants", {}).get("nodes", [])
                    all_deny = all(vn.get("inventoryPolicy") == "DENY" for vn in var_nodes)
                    has_delisted_tag = "supplier-delisted" in v_tags
                    no_shipping_tags = not any(st in [t.lower() for t in v_tags] for st in shipping_tags)

                    print(f"  Verification:")
                    print(f"    - Live Status:      {v_status} (Expected: DRAFT) -> {'PASS' if v_status == 'DRAFT' else 'FAIL'}")
                    print(f"    - 'supplier-delisted' in tags? {has_delisted_tag} -> {'PASS' if has_delisted_tag else 'FAIL'}")
                    print(f"    - Active shipping tags removed? {no_shipping_tags} -> {'PASS' if no_shipping_tags else 'FAIL'}")
                    print(f"    - All variants policy == DENY? {all_deny} ({len(var_nodes)} variants) -> {'PASS' if all_deny else 'FAIL'}")

                    if v_status == "DRAFT" and has_delisted_tag and all_deny:
                        remediated_count += 1
                        results.append({"handle": handle, "shopify_id": shopify_id, "status": "VERIFIED_DRAFT"})
                    else:
                        failed_count += 1
                        results.append({"handle": handle, "shopify_id": shopify_id, "status": "VERIFY_FAILED"})
                else:
                    print(f"  Verify Query Error: {v_err}")
                    failed_count += 1
            else:
                print(f"  Shopify Push Failed: {err}")
                failed_count += 1
        else:
            print("  Warning: No shopify_product_id on local product.")
            remediated_count += 1

    # Rebuild index
    build_and_save_index()
    print("\n" + "=" * 80)
    print(f"REMEDIATION COMPLETE: {remediated_count} Remediated | {failed_count} Failed")
    print("=" * 80)
    return {"remediated": remediated_count, "failed": failed_count, "results": results}


if __name__ == "__main__":
    remediate_stale_jdsports_products()
