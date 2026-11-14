import os
import sys
import json
import time

PROJECT_ROOT = "product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_sync import upsert_product_to_shopify
from storage.forex import get_usd_to_inr_rate

PILOT_FILES = {
    "Glossier": "00746b4ef0f45103.json",
    "MAKEUP BY MARIO": "0263b15b38529dfe.json",
    "Gisou": "026b5e220a9f4985.json",
    "REFY": "028a15e63b2cb6f9.json",
    "Haus Labs": "034159e1dcfe57b9.json",
    "Hourglass": "04c4dd45f575ba41.json",
    "PATRICK TA": "050a2d8ca25205a5.json",
    "Summer Fridays": "05266852db888a70.json",
    "Tower 28 Beauty": "05824dadb0d3488f.json",
    "MERIT": "064cffc5d3a5b0a4.json",
    "rhode": "0749eca097bf76c1.json",
    "Saie": "08702e1da9320ab5.json",
    "Kosas": "09fb3e7f2425a515.json",
    "Westman Atelier": "14f3a9acb4683314.json"
}

def main():
    print("=" * 80)
    print("STARTING SEPHORA PILOT INGESTION (14 LUXURY BEAUTY PRODUCTS)")
    print("=" * 80)

    rate = get_usd_to_inr_rate()
    print(f"Current Forex Rate USD->INR: {rate}")

    results = []
    for brand, fn in PILOT_FILES.items():
        fp = os.path.join(PROJECT_ROOT, "storage", "db", "sephora", "products", fn)
        with open(fp, "r", encoding="utf-8") as f:
            p = json.load(f)

        print(f"\nIngesting [{brand}] {p.get('title')[:45]}...")
        ok, p_node, err = upsert_product_to_shopify(p, forex_rate=rate)
        if ok and p_node:
            gid = p_node.get("id")
            handle = p_node.get("handle")
            print(f"  -> SUCCESS! GID: {gid} | Handle: {handle}")
            
            # Save shopify_product_id back to local record
            p["shopify_product_id"] = gid
            p["shopify_handle"] = handle
            p["shopify_synced_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(p, f, indent=2, ensure_ascii=False)
            
            results.append({"brand": brand, "title": p.get("title"), "handle": handle, "gid": gid, "success": True})
        else:
            print(f"  -> FAILED: {err}")
            results.append({"brand": brand, "title": p.get("title"), "error": err, "success": False})

    print("\n" + "=" * 80)
    print("PILOT INGESTION SUMMARY:")
    success_cnt = sum(1 for r in results if r["success"])
    print(f"Total: {len(results)} | Successful: {success_cnt} | Failed: {len(results) - success_cnt}")
    print("=" * 80)

if __name__ == "__main__":
    main()
