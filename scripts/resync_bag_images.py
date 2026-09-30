"""
High-Throughput Shopify Bag Re-sync Engine
Re-syncs affected luxury bag products so their featured media (files[0]) and default variant (variant[0])
match their authentic colorway and title.
"""
import os
import sys
import json
import glob
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_sync import upsert_product_to_shopify
from storage.forex import get_usd_to_inr_rate
from storage.logger import log_info, log_success, log_warning, log_error

def resync_products(store: str = "jwpei", filter_keyword: str = None, max_workers: int = 3):
    files = glob.glob(os.path.join(PROJECT_ROOT, "storage", "db", store, "products", "*.json"))
    print(f"Found {len(files)} products in {store} catalog.")

    forex_rate = get_usd_to_inr_rate()
    target_prods = []

    for fpath in files:
        with open(fpath, "r", encoding="utf-8") as f:
            prod = json.load(f)

        if filter_keyword and filter_keyword.lower() not in prod.get("title", "").lower():
            continue

        # Ensure top-level image / image_url is populated with authentic primary image
        imgs = prod.get("images") or []
        if imgs:
            prod["image"] = imgs[0]
            prod["image_url"] = imgs[0]
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(prod, f, indent=2, ensure_ascii=False)

        if prod.get("shopify_product_id"):
            target_prods.append((fpath, prod))

    print(f"Targeting {len(target_prods)} products for Shopify Admin GraphQL re-sync...")

    success_count = 0
    fail_count = 0
    start_time = time.time()

    def _sync_worker(item):
        fpath, prod = item
        try:
            ok, pnode, err = upsert_product_to_shopify(prod, forex_rate)
            return ok, prod.get("title"), prod.get("shopify_product_id"), err
        except Exception as exc:
            return False, prod.get("title"), prod.get("shopify_product_id"), str(exc)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_sync_worker, item): item for item in target_prods}
        for future in as_completed(futures):
            ok, title, pid, err = future.result()
            if ok:
                success_count += 1
                if success_count % 10 == 0 or len(target_prods) <= 25:
                    print(f"[{success_count}/{len(target_prods)}] Synced: {title[:40]} ({pid})")
            else:
                fail_count += 1
                print(f"[ERROR] Failed: {title[:40]} ({pid}) - {err}")

    elapsed = time.time() - start_time
    print("=" * 70)
    print(f"RE-SYNC COMPLETE: {success_count} succeeded, {fail_count} failed in {elapsed:.1f}s")
    print("=" * 70)

if __name__ == "__main__":
    kw = sys.argv[1] if len(sys.argv) > 1 else None
    store_arg = sys.argv[2] if len(sys.argv) > 2 else "jwpei"
    resync_products(store=store_arg, filter_keyword=kw)
