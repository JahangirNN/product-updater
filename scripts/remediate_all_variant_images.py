"""
High-Throughput Shopify Variant Image Remediation & Synchronization Engine
Remediates all catalog products on Shopify Admin GraphQL:
1. Links authentic variant image files to every variant.
2. Formats options to authentic dimensions ('Color', 'Size', 'Case Diameter').
3. Prunes un-photographed ghost variants.
4. Enforces ADR 0015 active inventory policies ('CONTINUE' if in stock).
5. Ensures single-variant items also have their featured image attached.
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
from storage.shopify_taxonomy import resolve_variant_image, BROKEN_IMAGE_URLS
from storage.logger import log_info, log_success, log_warning, log_error


def collect_remediation_candidates(
    stores: Optional[List[str]] = None,
    include_single_variant: bool = True
) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Collect all products synced to Shopify that require variant image linkage.
    """
    if not stores:
        stores = ["coach", "jwpei", "michaelkors", "jomashop"]

    candidates = []
    for s in stores:
        pattern = os.path.join(PROJECT_ROOT, "storage", "db", s, "products", "*.json")
        for f in glob.glob(pattern):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
            except Exception:
                continue

            pid = data.get("shopify_product_id")
            if not pid:
                continue

            variants = data.get("variants") or []
            if len(variants) > 1:
                # Multi-variant product
                candidates.append((f, data))
            elif include_single_variant:
                # Single variant product
                candidates.append((f, data))

    return candidates


def _remediate_worker(item, forex_rate, stats, lock, total):
    fpath, prod = item
    pid = prod.get("shopify_product_id")
    handle = prod.get("shopify_handle") or prod.get("handle")
    title = prod.get("title", "")[:35]

    ok, p_node, err = False, None, ""
    for attempt in range(1, 4):
        ok, p_node, err = upsert_product_to_shopify(prod, forex_rate)
        if ok:
            break
        if "throttled" in str(err).lower() or "429" in str(err):
            time.sleep(2.0 * attempt)
        else:
            time.sleep(0.5)

    with lock:
        stats["processed"] += 1
        current = stats["processed"]
        if ok:
            stats["success"] += 1
            if current % 10 == 0 or current == total:
                print(f"[{current:4d}/{total}] OK -> {handle:42} | {title}")
            
            # Update local record with latest sync timestamp
            try:
                prod["shopify_synced_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                with open(fpath, "w", encoding="utf-8") as fp:
                    json.dump(prod, fp, indent=2, ensure_ascii=False)
            except Exception:
                pass
        else:
            stats["failed"] += 1
            print(f"[{current:4d}/{total}] FAILED -> {handle:42} | Error: {err}")
            stats["errors"].append({"handle": handle, "id": pid, "error": err})


def run_remediation(
    stores: Optional[List[str]] = None,
    limit: Optional[int] = None,
    workers: int = 4,
    include_single_variant: bool = True
):
    print("=" * 80)
    print(f"STARTING CATALOG VARIANT IMAGE REMEDIATION PIPELINE")
    print(f"Stores: {stores or 'ALL (coach, jwpei, michaelkors, jomashop)'} | Workers: {workers}")
    print("=" * 80)

    forex_rate = get_usd_to_inr_rate()
    candidates = collect_remediation_candidates(stores=stores, include_single_variant=include_single_variant)
    print(f"Discovered {len(candidates)} synced products for remediation.")

    if limit and limit > 0:
        candidates = candidates[:limit]
        print(f"Applied limit: running remediation on first {len(candidates)} products.")

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
            executor.submit(_remediate_worker, item, forex_rate, stats, lock, total)
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
    print(f"REMEDIATION PIPELINE COMPLETED IN {elapsed:.1f}s")
    print(f"Total Processed: {stats['processed']}/{total}")
    print(f"Success: {stats['success']} | Failed: {stats['failed']}")
    if stats["errors"]:
        print(f"First 5 Errors:")
        for err_item in stats["errors"][:5]:
            print(f"  - {err_item}")
    print("=" * 80)
    return stats


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Remediate all variant images on Shopify")
    parser.add_argument("--stores", nargs="+", default=["coach", "jwpei", "michaelkors"], help="Stores to process")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of products to process")
    parser.add_argument("--workers", type=int, default=4, help="Number of concurrent workers")
    parser.add_argument("--multi-only", action="store_true", help="Only process multi-variant products")
    args = parser.parse_args()

    include_single = not args.multi_only
    run_remediation(stores=args.stores, limit=args.limit, workers=args.workers, include_single_variant=include_single)
