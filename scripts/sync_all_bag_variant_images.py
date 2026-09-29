"""
Shopify Variant Image Linker & Re-Sync Engine for Luxury Bags
Iterates through multi-variant bag products across COACH, JW PEI, and Michael Kors,
ensuring that every product variant is linked to its authentic colorway image on Shopify CDN.
"""
import os
import sys
import glob
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from storage.shopify_sync import upsert_product_to_shopify
from storage.forex import get_usd_to_inr_rate
from storage.logger import log_info, log_success, log_warning, log_error

def get_multi_variant_bag_products(store_filter: Optional[str] = None) -> List[Tuple[str, Dict[str, Any]]]:
    stores = ["jwpei", "coach", "michaelkors"]
    if store_filter and store_filter.lower() != "all":
        stores = [store_filter.lower()]

    candidates = []
    for s in stores:
        pattern = os.path.join(PROJECT_ROOT, "storage", "db", s, "products", "*.json")
        for f in glob.glob(pattern):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
            except Exception:
                continue

            # Must be synced to Shopify and have multiple variants
            pid = data.get("shopify_product_id")
            variants = data.get("variants") or []
            if not pid or len(variants) <= 1:
                continue

            # Must have variant images
            has_var_imgs = any(v.get("image_url") or v.get("image") for v in variants if isinstance(v, dict))
            if has_var_imgs:
                candidates.append((f, data))

    return candidates


def _sync_worker(item, forex_rate, stats, lock, total):
    fpath, prod = item
    pid = prod.get("shopify_product_id")
    handle = prod.get("shopify_handle") or prod.get("handle")
    title = prod.get("title", "")[:35]

    ok, p_node, err = upsert_product_to_shopify(prod, forex_rate)

    with lock:
        stats["processed"] += 1
        current = stats["processed"]
        if ok:
            stats["success"] += 1
            if current % 10 == 0 or current == total:
                print(f"[{current}/{total}] OK -> {handle:40} | {title}")
        else:
            stats["failed"] += 1
            print(f"[{current}/{total}] FAILED -> {handle:40} | Error: {err}")
            stats["errors"].append({"handle": handle, "id": pid, "error": err})


def run_sync(store: Optional[str] = None, limit: Optional[int] = None, workers: int = 6):
    print("=" * 80)
    print(f"SYNCING BAG VARIANT IMAGES TO SHOPIFY | Store: {store or 'ALL'} | Workers: {workers}")
    print("=" * 80)

    forex_rate = get_usd_to_inr_rate()
    candidates = get_multi_variant_bag_products(store_filter=store)
    print(f"Found {len(candidates)} multi-variant bag candidates.")

    if limit and limit > 0:
        candidates = candidates[:limit]
        print(f"Applied limit: processing {len(candidates)} bags.")

    stats = {
        "processed": 0,
        "success": 0,
        "failed": 0,
        "errors": []
    }
    lock = threading.Lock()
    total = len(candidates)

    start_time = time.time()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(_sync_worker, item, forex_rate, stats, lock, total)
            for item in candidates
        ]
        for f in as_completed(futures):
            try:
                f.result()
            except Exception as e:
                with lock:
                    stats["failed"] += 1
                    stats["errors"].append({"error": str(e)})

    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"SYNC COMPLETED in {elapsed:.1f}s | Success: {stats['success']}/{total} | Failed: {stats['failed']}")
    print("=" * 80)
    return stats


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sync bag variant images to Shopify")
    parser.add_argument("--store", type=str, default="all")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()

    run_sync(store=args.store, limit=args.limit, workers=args.workers)
