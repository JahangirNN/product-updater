import os
import sys
import json
import time
import glob

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_sync import upsert_product_to_shopify
from storage.forex import get_usd_to_inr_rate

TARGET_GROUPS = [
    {
        "store": "nordstrom",
        "dir": os.path.join(PROJECT_ROOT, "storage/db/nordstrom/products"),
        "filter": lambda p: "tory burch" in str(p.get("brand") or p.get("vendor") or "").lower() or "tory burch" in str(p.get("title") or "").lower()
    },
    {
        "store": "nordstromrack",
        "dir": os.path.join(PROJECT_ROOT, "storage/db/nordstromrack/products"),
        "filter": lambda p: any(b in str(p.get("brand") or p.get("vendor") or "").lower() for b in ["marc jacobs", "kurt geiger"]) or any(b in str(p.get("title") or "").lower() for b in ["marc jacobs", "kurt geiger"])
    },
    {
        "store": "jomashop",
        "dir": os.path.join(PROJECT_ROOT, "storage/db/jomashop/products"),
        "filter": lambda p: any(b in str(p.get("brand") or p.get("vendor") or "").lower() for b in ["carrera", "oakley", "hugo boss", "boss", "miu miu", "calvin klein", "tory burch"]) or any(b in str(p.get("title") or "").lower() for b in ["carrera", "oakley", "hugo boss", "miu miu", "calvin klein", "tory burch"])
    }
]

def collect_target_files():
    targets = []
    for grp in TARGET_GROUPS:
        files = glob.glob(f"{grp['dir']}/*.json")
        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                if grp["filter"](data):
                    targets.append((f, data))
            except Exception as e:
                pass
    return targets

def sync_catalog():
    print("=" * 80)
    print("STARTING FULL BATCH INGESTION: 417 HANDBAGS & DESIGNER SUNGLASSES")
    print("=" * 80)

    rate = get_usd_to_inr_rate()
    print(f"Current Forex Rate USD->INR: {rate:.4f}\n")

    targets = collect_target_files()
    total = len(targets)
    print(f"Total target products matched: {total}")

    success_cnt = 0
    fail_cnt = 0
    skipped_cnt = 0

    start_time = time.time()

    for idx, (fp, p) in enumerate(targets, 1):
        title = p.get("title", "")
        brand = p.get("brand") or p.get("vendor") or ""

        # Skip if already imported with valid GID
        if p.get("shopify_product_id") and p.get("shopify_synced_at"):
            skipped_cnt += 1
            if idx % 25 == 0 or idx == total:
                elapsed = time.time() - start_time
                print(f"[{idx}/{total}] (Skipped/Existing) [{brand}] {title[:30]} | Success: {success_cnt}, Skipped: {skipped_cnt}, Failed: {fail_cnt} ({elapsed:.1f}s)")
            continue

        try:
            ok, p_node, err = upsert_product_to_shopify(p, forex_rate=rate)
            if ok and p_node:
                gid = p_node.get("id")
                handle = p_node.get("handle")
                p["shopify_product_id"] = gid
                p["shopify_handle"] = handle
                p["shopify_synced_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                p["shopify_sync_pending"] = False

                with open(fp, "w", encoding="utf-8") as f:
                    json.dump(p, f, indent=2, ensure_ascii=False)
                success_cnt += 1
            else:
                fail_cnt += 1
                print(f"[{idx}/{total}] FAILED [{brand}] {title[:30]}: {err}")

            if idx % 25 == 0 or idx == total:
                elapsed = time.time() - start_time
                print(f"[{idx}/{total}] Progress: Success: {success_cnt}, Skipped: {skipped_cnt}, Failed: {fail_cnt} (Elapsed: {elapsed:.1f}s)")

            # Sleep slightly to respect Shopify GraphQL bucket capacity
            time.sleep(0.35)

        except Exception as e:
            fail_cnt += 1
            print(f"[{idx}/{total}] EXCEPTION on {fp}: {e}")

    total_time = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"BATCH INGESTION COMPLETE in {total_time:.1f}s")
    print(f"Total: {total} | Success: {success_cnt} | Skipped: {skipped_cnt} | Failed: {fail_cnt}")
    print("=" * 80)

if __name__ == "__main__":
    sync_catalog()
