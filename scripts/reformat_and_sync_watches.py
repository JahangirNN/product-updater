"""
Batch Watch Reformatting, Leakage Sanitizer & Shopify Sync Engine
1. Formats all 574 watch records with the world-class Luxury Watch PDP template.
2. Scrubs all supplier leaks (Jomashop Sku, Jomashop Warranty, Jomashop tags).
3. Updates local JSON files atomically.
4. Pushes updated luxury descriptions, tags, and specifications to Shopify Admin GraphQL.
Adheres to ADR 0005, 0006, 0015, 0020, and 0021.
"""
import os
import sys
import glob
import json
import time
import argparse
from typing import Dict, Any, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from storage.shopify_taxonomy import format_luxury_watch_description_html
from storage.shopify_sync import upsert_product_to_shopify
from storage.forex import get_usd_to_inr_rate
from storage.logger import log_info, log_success, log_warning, log_error


def clean_and_update_local_watch_records() -> List[Dict[str, Any]]:
    """
    Sanitize and update all local watch product JSON files.
    """
    db_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "db", "jomashop", "products")
    files = glob.glob(os.path.join(db_root, "*.json"))
    
    print(f"[*] Found {len(files)} total watch files to reformat and sanitize.")
    updated_products = []

    for idx, fp in enumerate(files, 1):
        with open(fp, "r", encoding="utf-8") as f:
            p = json.load(f)

        # 1. Clean specifications
        specs = p.get("specifications") or {}
        if "Jomashop Sku" in specs:
            specs["Model SKU"] = specs.pop("Jomashop Sku")
        if "Warranty" in specs:
            specs["Warranty"] = "2-Year International Luxury Warranty"
        p["specifications"] = specs

        # 2. Clean tags
        tags = p.get("tags") or []
        tags = [t for t in tags if not any(leak in t.lower() for leak in ["jomashop", "nordstrom", "footlocker", "finishline", "jdsports"])]
        p["tags"] = tags

        # 3. Generate high-end luxury description HTML
        new_html = format_luxury_watch_description_html(p)
        p["descriptionHtml"] = new_html

        # 4. Save back to disk
        tmp_fp = f"{fp}.tmp"
        with open(tmp_fp, "w", encoding="utf-8") as f:
            json.dump(p, f, indent=2, ensure_ascii=False)
        os.replace(tmp_fp, fp)

        updated_products.append(p)

    print(f"[SUCCESS] All {len(updated_products)} local watch files sanitized and reformatted on disk.")
    return updated_products


def sync_watches_to_shopify(products: List[Dict[str, Any]], limit: int = None, delay: float = 0.15, max_workers: int = 3):
    """
    Push updated descriptions and tags to Shopify Admin GraphQL concurrently.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading

    forex_rate = get_usd_to_inr_rate()
    log_info(f"Using forex rate: 1 USD = INR {forex_rate:.2f}")

    to_sync = products if not limit else products[:limit]
    print(f"[*] Starting concurrent Shopify sync for {len(to_sync)} watches ({max_workers} workers)...")

    succeeded = 0
    failed = 0
    lock = threading.Lock()
    start_time = time.time()
    counter = 0

    def _worker(prod: Dict[str, Any]) -> Tuple[bool, str, str]:
        nonlocal counter
        title = prod.get("title", "")[:40]
        shop_id = prod.get("shopify_product_id", "")
        
        ok, p_node, err = upsert_product_to_shopify(prod, forex_rate)
        with lock:
            counter += 1
            idx = counter
            if ok and p_node:
                print(f"[{idx}/{len(to_sync)}] OK -> '{title}' ({shop_id})")
            else:
                print(f"[{idx}/{len(to_sync)}] FAIL -> '{title}' ({shop_id}): {err}")
        time.sleep(delay)
        return ok, shop_id, err

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_worker, prod) for prod in to_sync]
        for f in as_completed(futures):
            ok, shop_id, err = f.result()
            if ok:
                succeeded += 1
            else:
                failed += 1

    elapsed = time.time() - start_time
    print("=" * 80)
    print(f"WATCH SHOPIFY SYNC COMPLETE in {elapsed:.1f}s")
    print(f"Total: {len(to_sync)} | Succeeded: {succeeded} | Failed: {failed}")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Reformat Watch PDPs and Sync to Shopify")
    parser.add_argument("--local-only", action="store_true", help="Only reformat local JSON files without syncing to Shopify")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of watches to sync to Shopify")
    parser.add_argument("--delay", type=float, default=0.25, help="Inter-request delay in seconds")

    args = parser.parse_args()

    products = clean_and_update_local_watch_records()

    if not args.local_only:
        sync_watches_to_shopify(products, limit=args.limit, delay=args.delay)


if __name__ == "__main__":
    main()
