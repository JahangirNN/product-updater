import os
import sys
import json
import time

PROJECT_ROOT = "product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_sync import upsert_product_to_shopify
from storage.forex import get_usd_to_inr_rate

def sync_full_catalog():
    print("=" * 80)
    print("STARTING FULL SEPHORA CATALOG INGESTION (547 LUXURY BEAUTY PRODUCTS)")
    print("=" * 80)

    rate = get_usd_to_inr_rate()
    print(f"Current Forex Rate USD->INR: {rate}\n")

    p_dir = os.path.join(PROJECT_ROOT, "storage", "db", "sephora", "products")
    files = [fn for fn in os.listdir(p_dir) if fn.endswith(".json")]
    total = len(files)
    print(f"Total Sephora products in catalog: {total}")

    success_cnt = 0
    fail_cnt = 0
    skipped_cnt = 0

    for idx, fn in enumerate(files, 1):
        fp = os.path.join(p_dir, fn)
        try:
            with open(fp, "r", encoding="utf-8") as f:
                p = json.load(f)

            title = p.get("title", "")
            brand = p.get("brand") or p.get("vendor") or ""

            # Check if already synced and has active GID
            if p.get("shopify_product_id") and p.get("shopify_synced_at"):
                skipped_cnt += 1
                if idx % 25 == 0 or idx == total:
                    print(f"[{idx}/{total}] (Skipped/Existing) [{brand}] {title[:35]} (Success: {success_cnt}, Skipped: {skipped_cnt}, Failed: {fail_cnt})")
                continue

            ok, p_node, err = upsert_product_to_shopify(p, forex_rate=rate)
            if ok and p_node:
                gid = p_node.get("id")
                handle = p_node.get("handle")
                p["shopify_product_id"] = gid
                p["shopify_handle"] = handle
                p["shopify_synced_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                with open(fp, "w", encoding="utf-8") as f:
                    json.dump(p, f, indent=2, ensure_ascii=False)
                success_cnt += 1
            else:
                fail_cnt += 1
                print(f"[{idx}/{total}] FAILED [{brand}] {title[:35]}: {err}")

            if idx % 10 == 0 or idx == total:
                print(f"[{idx}/{total}] Progress: Success: {success_cnt}, Skipped: {skipped_cnt}, Failed: {fail_cnt}")

            # Sleep slightly to respect Shopify GraphQL bucket capacity
            time.sleep(0.35)

        except Exception as e:
            fail_cnt += 1
            print(f"[{idx}/{total}] EXCEPTION on {fn}: {e}")

    print("\n" + "=" * 80)
    print("FULL CATALOG INGESTION COMPLETE")
    print(f"Total: {total} | Successfully Synced: {success_cnt} | Already Synced: {skipped_cnt} | Failed: {fail_cnt}")
    print("=" * 80)

if __name__ == "__main__":
    sync_full_catalog()
