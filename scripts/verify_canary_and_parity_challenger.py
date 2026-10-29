"""
Empirical Challenger Script for Canary Verification & Catalog Parity
Run by challenger_m1_2.
"""
import os
import sys
import json
import glob
import random
import hashlib
from typing import Dict, Any, List, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from storage.shopify_auth import execute_shopify_graphql

CANARY_GID = "gid://shopify/Product/15838215667878"
CANARY_LOCAL_ID = "009e74a980966b3c"
CANARY_LOCAL_PATH = os.path.join("storage", "db", "jomashop", "products", f"{CANARY_LOCAL_ID}.json")

def verify_canary_live() -> Dict[str, Any]:
    query = """
    query getProduct($id: ID!) {
      product(id: $id) {
        id
        title
        handle
        status
        totalVariants
        tags
        variants(first: 5) {
          nodes {
            id
            title
            sku
            price
            compareAtPrice
            inventoryQuantity
            inventoryItem {
              id
            }
          }
        }
      }
    }
    """
    data, ext, err = execute_shopify_graphql(query, variables={"id": CANARY_GID})
    if err or not data or not data.get("product"):
        return {"error": f"Failed to query Shopify product: {err}"}
    return data["product"]

def verify_canary_disk() -> Dict[str, Any]:
    if not os.path.exists(CANARY_LOCAL_PATH):
        return {"error": f"File does not exist: {CANARY_LOCAL_PATH}"}
    with open(CANARY_LOCAL_PATH, "rb") as f:
        raw_bytes = f.read()
    sha256_hash = hashlib.sha256(raw_bytes).hexdigest()
    text = raw_bytes.decode("utf-8")
    data = json.loads(text)
    return {
        "file_path": CANARY_LOCAL_PATH,
        "byte_size": len(raw_bytes),
        "sha256": sha256_hash,
        "json_data": data
    }

def search_compare_at_93636() -> List[Dict[str, Any]]:
    matches = []
    files = glob.glob(os.path.join("storage", "db", "jomashop", "products", "*.json"))
    for fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                d = json.load(f)
            cap = d.get("compare_at_price")
            scap = d.get("source_compare_at_price")
            cp = d.get("current_price")
            sp = d.get("source_price")
            v0 = (d.get("variants") or [{}])[0]
            v_cap = v0.get("compare_at_price")
            
            # Check for 93636 in any price field
            if any(str(x) in ("93636", "93636.0", "93636.00") for x in (cap, scap, cp, sp, v_cap)):
                matches.append({
                    "file": fpath,
                    "id": d.get("id"),
                    "title": d.get("title"),
                    "compare_at_price": cap,
                    "source_compare_at_price": scap
                })
        except Exception:
            pass
    return matches

def sample_multi_brand_parity(sample_per_brand: int = 3) -> Dict[str, Any]:
    brands = ["Versace", "Tissot", "Seiko", "Citizen", "Michael Kors"]
    brand_files: Dict[str, List[str]] = {b: [] for b in brands}
    
    all_files = glob.glob(os.path.join("storage", "db", "jomashop", "products", "*.json"))
    for fpath in all_files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                d = json.load(f)
            v = d.get("vendor") or ""
            for b in brands:
                if b.lower() == v.lower():
                    brand_files[b].append(fpath)
                    break
        except Exception:
            pass

    sampled_products: List[Dict[str, Any]] = []
    random.seed(42)  # Deterministic seed for reproducible testing
    for b in brands:
        flist = brand_files[b]
        sampled = random.sample(flist, min(sample_per_brand, len(flist)))
        for s in sampled:
            with open(s, "r", encoding="utf-8") as f:
                d = json.load(f)
            sampled_products.append({
                "brand": b,
                "file": s,
                "id": d.get("id"),
                "shopify_product_id": d.get("shopify_product_id"),
                "handle": d.get("handle"),
                "title": d.get("title"),
                "availability": d.get("availability"),
                "source_price": d.get("source_price"),
                "current_price": d.get("current_price"),
                "compare_at_price": d.get("compare_at_price"),
                "variant_price": (d.get("variants") or [{}])[0].get("price"),
                "variant_compare_at": (d.get("variants") or [{}])[0].get("compare_at_price"),
            })

    # Batch query live Shopify
    gids = [p["shopify_product_id"] for p in sampled_products if p.get("shopify_product_id")]
    query = """
    query getNodes($ids: [ID!]!) {
      nodes(ids: $ids) {
        ... on Product {
          id
          title
          handle
          status
          totalVariants
          variants(first: 5) {
            nodes {
              id
              sku
              price
              compareAtPrice
              inventoryQuantity
            }
          }
        }
      }
    }
    """
    data, ext, err = execute_shopify_graphql(query, variables={"ids": gids})
    if err or not data:
        return {"error": f"Failed to batch query Shopify nodes: {err}", "sampled": sampled_products}
    
    live_nodes = {n["id"]: n for n in data.get("nodes", []) if n and "id" in n}

    comparisons = []
    all_matched = True
    for p in sampled_products:
        gid = p.get("shopify_product_id")
        live = live_nodes.get(gid)
        if not live:
            comparisons.append({
                "brand": p["brand"],
                "local_id": p["id"],
                "gid": gid,
                "error": "Not found on Shopify"
            })
            all_matched = False
            continue

        live_variants = live.get("variants", {}).get("nodes", [])
        v0 = live_variants[0] if live_variants else {}
        live_price = v0.get("price")
        live_compare_at = v0.get("compareAtPrice")

        # Title match (exact or prefix)
        title_match = (p["title"].strip() == live["title"].strip())
        handle_match = (p["handle"].strip() == live["handle"].strip())
        
        # Whole rupee check
        is_whole_rupee = False
        try:
            is_whole_rupee = (float(live_price).is_integer() and live_price.endswith(".00"))
        except Exception:
            pass

        # Price comparison
        expected_price_str = f"{float(p['current_price']):.2f}"
        price_match = (live_price == expected_price_str or abs(float(live_price) - float(p['current_price'])) <= 100) # Check tolerance / exact
        exact_price_match = (live_price == expected_price_str)

        comp = {
            "brand": p["brand"],
            "local_id": p["id"],
            "gid": gid,
            "title_local": p["title"],
            "title_live": live["title"],
            "title_match": title_match,
            "handle_local": p["handle"],
            "handle_live": live["handle"],
            "handle_match": handle_match,
            "live_status": live["status"],
            "local_availability": p["availability"],
            "local_inr_price": expected_price_str,
            "live_inr_price": live_price,
            "exact_price_match": exact_price_match,
            "price_diff": round(float(live_price) - float(p['current_price']), 2),
            "is_whole_rupee": is_whole_rupee,
            "local_compare_at": f"{float(p['compare_at_price']):.2f}" if p.get('compare_at_price') else None,
            "live_compare_at": live_compare_at,
        }
        comparisons.append(comp)

    return {
        "sampled_count": len(sampled_products),
        "comparisons": comparisons
    }

def main():
    print("========================================================================")
    print("CHALLENGER VERIFICATION: CANARY & CATALOG PARITY")
    print("========================================================================")

    # 1. CANARY LIVE
    print("\n--- 1. Live Shopify Verification of Canary ---")
    canary_live = verify_canary_live()
    print(f"Product GID:       {canary_live.get('id')}")
    print(f"Title:             {canary_live.get('title')}")
    print(f"Handle:            {canary_live.get('handle')}")
    print(f"Status:            {canary_live.get('status')}")
    print(f"Total Variants:    {canary_live.get('totalVariants')}")
    print(f"Tags:              {canary_live.get('tags')}")
    variants = canary_live.get("variants", {}).get("nodes", [])
    if variants:
        v = variants[0]
        print(f"Variant ID:        {v.get('id')}")
        print(f"SKU:               {v.get('sku')}")
        print(f"Live Price:        INR {v.get('price')}")
        print(f"Live CompareAt:    INR {v.get('compareAtPrice')}")
        print(f"Inventory Qty:     {v.get('inventoryQuantity')}")

    # 2. CANARY DISK
    print("\n--- 2. Local Canary Disk Verification ---")
    canary_disk = verify_canary_disk()
    if "error" in canary_disk:
        print(f"ERROR: {canary_disk['error']}")
    else:
        d = canary_disk["json_data"]
        print(f"Local File:        {canary_disk['file_path']}")
        print(f"Byte Size:         {canary_disk['byte_size']} bytes")
        print(f"SHA-256:           {canary_disk['sha256']}")
        print(f"Source Price USD:  ${d.get('source_price')}")
        print(f"Current Price INR: INR {d.get('current_price')}")
        print(f"Compare At INR:    INR {d.get('compare_at_price')}")
        print(f"Forex Rate Used:   {d.get('forex_rate_used')}")
        print(f"Availability:      {d.get('availability')}")
        print(f"Shopify Product ID:{d.get('shopify_product_id')}")

    # 3. SEARCH 93636
    print("\n--- 3. Search for compare_at_price 93636 across local DB ---")
    m93636 = search_compare_at_93636()
    print(f"Matches found for 93636: {len(m93636)}")
    for m in m93636:
        print(f"  {m}")

    # 4. RANDOM SAMPLE PARITY ACROSS 5 BRANDS
    print("\n--- 4. Multi-Brand Random Sample Parity (5 Brands x 3 Products = 15 Total) ---")
    parity_results = sample_multi_brand_parity(sample_per_brand=3)
    if "error" in parity_results:
        print(f"ERROR: {parity_results['error']}")
    else:
        print(f"Total Sampled: {parity_results['sampled_count']}")
        for comp in parity_results["comparisons"]:
            print(f"[{comp.get('brand')}] {comp.get('title_local')[:35]}...")
            print(f"  GID: {comp.get('gid')}")
            print(f"  Title Match: {comp.get('title_match')} | Handle Match: {comp.get('handle_match')}")
            print(f"  Status: {comp.get('live_status')} (Local: {comp.get('local_availability')})")
            print(f"  Local Price: INR {comp.get('local_inr_price')} | Live Price: INR {comp.get('live_inr_price')} (Exact Match: {comp.get('exact_price_match')}, Diff: {comp.get('price_diff')})")
            print(f"  Whole Rupee (.00): {comp.get('is_whole_rupee')}")
            print(f"  Local CompareAt: INR {comp.get('local_compare_at')} | Live CompareAt: INR {comp.get('live_compare_at')}")

    # Save evidence artifact
    challenger_evidence_path = os.path.join(
        r"c:\Users\Administrator\WorkPlace\dropship-scraper-portable-20260905\product-updater\.agents\challenger_m1_2",
        "challenger_parity_evidence.json"
    )
    with open(challenger_evidence_path, "w", encoding="utf-8") as out:
        json.dump({
            "canary_live": canary_live,
            "canary_disk": canary_disk,
            "matches_93636": m93636,
            "parity_results": parity_results
        }, out, indent=2)
    print(f"\nSaved challenger evidence to: {challenger_evidence_path}")

    # Inspect Tsuyosa watch
    print("\n--- 5. Inspect Tsuyosa Watch (gid://shopify/Product/15838879776934) ---")
    files = glob.glob(os.path.join("storage", "db", "jomashop", "products", "*.json"))
    for fpath in files:
        with open(fpath, "r", encoding="utf-8") as f:
            d = json.load(f)
        if d.get("shopify_product_id") == "gid://shopify/Product/15838879776934":
            print(f"File: {fpath}")
            print(f"Local Availability: {d.get('availability')}")
            print(f"Local Is Active: {d.get('is_active')}")
            print(f"Variants in_stock: {[v.get('in_stock') for v in d.get('variants', [])]}")
            print(f"Shopify Synced At: {d.get('shopify_synced_at')}")
            print(f"Last Verified At: {d.get('last_verified_at')}")
            break
    print("========================================================================")

if __name__ == "__main__":
    main()
