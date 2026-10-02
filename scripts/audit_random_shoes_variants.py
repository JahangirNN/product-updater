import os
import sys
import glob
import json
import random
from typing import List, Dict, Any

PROJECT_ROOT = r"c:\Users\Administrator\WorkPlace\dropship-scraper-portable-20260905\product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql
from storage.forex import get_usd_to_inr_rate
from storage.shopify_sync import upsert_product_to_shopify

rng = random.SystemRandom()

FOOTWEAR_KEYWORDS = [
    'sandal', 'shoe', 'sneaker', 'trainer', 'boot', 'pump',
    'loafer', 'slide', 'heel', 'mule', 'footwear', 'clog', 'flat'
]

def find_all_synced_shoes() -> Dict[str, List[Dict[str, Any]]]:
    catalog = {"coach": [], "michaelkors": []}
    for brand in ["coach", "michaelkors"]:
        files = glob.glob(os.path.join(PROJECT_ROOT, "storage", "db", brand, "products", "*.json"))
        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    prod = json.load(fp)
                if not prod.get("shopify_product_id"):
                    continue
                pt = str(prod.get("product_type", "")).lower()
                title = str(prod.get("title", "")).lower()
                tags = [str(t).lower() for t in prod.get("tags", [])]
                if any(k in pt or k in title or any(k in t for t in tags) for k in FOOTWEAR_KEYWORDS):
                    prod["_file_path"] = f
                    catalog[brand].append(prod)
            except Exception as e:
                pass
    return catalog

def query_live_shopify_product(shopify_id: str) -> Dict[str, Any]:
    query = """
    query getProductDetails($id: ID!) {
      product(id: $id) {
        id
        title
        handle
        status
        publishedAt
        onlineStoreUrl
        options {
          name
          values
        }
        variants(first: 50) {
          edges {
            node {
              id
              title
              sku
              price
              compareAtPrice
              inventoryPolicy
              inventoryItem {
                tracked
              }
              selectedOptions {
                name
                value
              }
            }
          }
        }
      }
    }
    """
    data, _, err = execute_shopify_graphql(query, {"id": shopify_id})
    if err or not data or not data.get("product"):
        return None
    return data["product"]

def run_random_audit():
    print("=" * 80)
    print("STARTING TRULY RANDOM SHOES VERIFICATION: COACH & MICHAEL KORS")
    print("=" * 80)

    catalog = find_all_synced_shoes()
    print(f"Total synced footwear discovered:")
    print(f"  - Coach Footwear: {len(catalog['coach'])} products")
    print(f"  - Michael Kors Footwear: {len(catalog['michaelkors'])} products")

    # Sample 4 random Coach shoes and 4 random Michael Kors shoes using SystemRandom
    sample_coach = rng.sample(catalog["coach"], min(4, len(catalog["coach"])))
    sample_mk = rng.sample(catalog["michaelkors"], min(4, len(catalog["michaelkors"])))

    all_samples = [("coach", p) for p in sample_coach] + [("michaelkors", p) for p in sample_mk]
    forex_rate = get_usd_to_inr_rate()
    print(f"Current USD->INR Forex Rate: {forex_rate}")

    audit_results = []

    for brand, local_prod in all_samples:
        pid = local_prod.get("id")
        title = local_prod.get("title")
        sp_id = local_prod.get("shopify_product_id")
        print("\n" + "-" * 70)
        print(f"BRAND: {brand.upper()} | PID: {pid} | GID: {sp_id}")
        print(f"Title: {title}")

        # Ensure our patched taxonomy handles variant stock correctly
        ok, _, up_err = upsert_product_to_shopify(local_prod, forex_rate)
        print(f"Sync check to Shopify: ok={ok} {up_err or ''}")

        live_p = query_live_shopify_product(sp_id)
        if not live_p:
            print(f"  FAILED to query Shopify for {sp_id}")
            continue

        live_status = live_p.get("status")
        live_published = live_p.get("publishedAt")
        print(f"  Shopify Status: {live_status} | PublishedAt: {live_published}")
        print(f"  Options: {[opt['name'] for opt in live_p.get('options', [])]}")

        live_variants = [edge["node"] for edge in live_p.get("variants", {}).get("edges", [])]
        local_variants = local_prod.get("variants", [])

        print(f"  Total Variants: Local={len(local_variants)} | Shopify={len(live_variants)}")

        # Verify individual variants
        variant_checks = []
        for lv in live_variants:
            v_title = lv["title"]
            v_sku = lv["sku"]
            v_price = lv["price"]
            v_policy = lv["inventoryPolicy"]
            v_tracked = lv["inventoryItem"]["tracked"]

            # Match with local variant
            matched_local = None
            for loc_v in local_variants:
                loc_sku = f"RARE-{loc_v.get('sku') or loc_v.get('id') or ''}"
                loc_title = loc_v.get("title") or loc_v.get("name")
                if loc_sku == v_sku or loc_title == v_title:
                    matched_local = loc_v
                    break

            loc_in_stock = None
            expected_policy = "CONTINUE"
            if matched_local:
                if "in_stock" in matched_local:
                    loc_in_stock = bool(matched_local.get("in_stock"))
                elif matched_local.get("availability") is not None:
                    loc_in_stock = (matched_local.get("availability") == "in_stock")
                else:
                    loc_in_stock = (local_prod.get("availability") == "in_stock") or (local_prod.get("in_stock") is True)
                expected_policy = "CONTINUE" if loc_in_stock else "DENY"

            policy_ok = (v_policy == expected_policy)
            # Price check: must end with .00 and be whole-rupee
            price_ok = v_price.endswith(".00")

            variant_checks.append({
                "title": v_title,
                "sku": v_sku,
                "price": v_price,
                "policy": v_policy,
                "tracked": v_tracked,
                "expected_policy": expected_policy,
                "loc_in_stock": loc_in_stock,
                "policy_ok": policy_ok,
                "price_ok": price_ok
            })

        all_policy_ok = all(vc["policy_ok"] for vc in variant_checks)
        all_price_ok = all(vc["price_ok"] for vc in variant_checks)

        print(f"  Variant Integrity: Policy Correctness={all_policy_ok} | Whole-Rupee INR={all_price_ok}")
        for vc in variant_checks[:4]:
            print(f"    - {vc['title']:20} | Price: {vc['price']:12} | Policy: {vc['policy']:8} (Expected: {vc['expected_policy']:8}) | Tracked: {vc['tracked']}")

        audit_results.append({
            "brand": brand,
            "id": pid,
            "title": title,
            "shopify_product_id": sp_id,
            "handle": live_p.get("handle"),
            "status": live_status,
            "published_at": live_published,
            "total_variants": len(live_variants),
            "all_policy_ok": all_policy_ok,
            "all_price_ok": all_price_ok,
            "variants_sample": variant_checks
        })

    out_file = os.path.join(PROJECT_ROOT, "scratch", "random_shoes_audit_report.json")
    with open(out_file, "w", encoding="utf-8") as fp:
        json.dump(audit_results, fp, indent=2)
    print("\n" + "=" * 80)
    print(f"RANDOM AUDIT COMPLETED: Saved detailed JSON report to {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    run_random_audit()
