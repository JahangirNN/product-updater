"""
Shopify Bulk Provisioning Engine for Luxury Bags & Leather Goods (Phase 3)
Provisions 1,199 luxury bags across COACH (414), JW PEI (491), and Michael Kors (294).
Uses pure functions, productSet GraphQL mutation, dynamic throttle budget tracking,
idempotent disk stamping, concurrent worker pool, and centralized catalog index rebuild.
Adheres to ADR 0005, ADR 0006, ADR 0015, ADR 0019, ADR 0020, ADR 0021.
"""
import os
import sys
import glob
import json
import time
import threading
import argparse
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
from storage.shopify_taxonomy import prepare_product_set_payload, resolve_authentic_vendor, resolve_luxury_bag_silhouette
from storage.forex import get_usd_to_inr_rate
from storage.db import build_and_save_index
from storage.logger import log_info, log_success, log_warning, log_error, log_shopify_error, log_shopify_success
from scripts.audit_luxury_bags_catalog import get_luxury_bag_products


def load_audited_bag_products(store_filter: Optional[str] = None, force: bool = False) -> List[Tuple[str, Dict[str, Any]]]:
    """Load the exact 1,199 audited bag products."""
    catalog = get_luxury_bag_products()
    candidates = []

    for brand, prods in catalog.items():
        if store_filter and store_filter.lower() != "all" and brand.lower() != store_filter.lower():
            continue
        for p in prods:
            if not force and p.get("shopify_product_id"):
                continue
            candidates.append((p["_file_path"], p))

    return candidates


def _provision_single_worker(item_data, forex_rate, stats, lock, total_count, delay):
    idx, fpath, prod = item_data
    pid = prod.get("id") or os.path.basename(fpath).replace(".json", "")
    title = prod.get("title", "")[:32]
    vendor = resolve_authentic_vendor(prod)
    sil = resolve_luxury_bag_silhouette(prod)

    ok, p_node, err = upsert_product_to_shopify(prod, forex_rate)

    with lock:
        current_num = stats["success"] + stats["failed"] + 1
        if ok and p_node:
            shop_id = p_node.get("id")
            handle = p_node.get("handle")
            print(f"[{current_num}/{total_count}] OK -> {vendor:18} | {sil:22} | {title} -> {shop_id}")

            # Stamp product file on disk
            prod["shopify_product_id"] = shop_id
            prod["shopify_handle"] = handle
            prod["shopify_synced_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            prod["shopify_sync_pending"] = False

            if "_file_path" in prod:
                del prod["_file_path"]

            try:
                with open(fpath, "w", encoding="utf-8") as pf:
                    json.dump(prod, pf, indent=2, ensure_ascii=False)
            except Exception as se:
                log_error(f"Failed to save stamped file {fpath}: {se}")

            stats["success"] += 1
        else:
            print(f"[{current_num}/{total_count}] FAILED -> {vendor:18} | {title}: {err}")
            stats["failed"] += 1
            stats["errors"].append({"id": pid, "title": title, "error": err})

    if delay > 0:
        time.sleep(delay)


def run_provisioning(
    store_filter: Optional[str] = None,
    limit: Optional[int] = None,
    dry_run: bool = False,
    force: bool = False,
    delay: float = 0.05,
    workers: int = 4
) -> Dict[str, Any]:
    print("=" * 80)
    print(f"LUXURY BAGS PROVISIONING | Store: {store_filter or 'ALL 3 (Coach, JW PEI, MK)'} | Workers: {workers} | DryRun: {dry_run}")
    print("=" * 80)

    forex_rate = get_usd_to_inr_rate()
    log_info(f"Loaded live forex rate: 1 USD = INR {forex_rate:.2f}")

    candidates = load_audited_bag_products(store_filter=store_filter, force=force)
    log_info(f"Loaded {len(candidates)} bag products ready for provisioning.")

    if limit and limit > 0:
        candidates = candidates[:limit]
        log_info(f"Applying limit: processing first {len(candidates)} items.")

    stats = {
        "total": len(candidates),
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "errors": []
    }

    if not candidates:
        log_info("No products to provision.")
        return stats

    if dry_run:
        for idx, (fpath, prod) in enumerate(candidates, 1):
            pid = prod.get("id") or os.path.basename(fpath).replace(".json", "")
            title = prod.get("title", "")[:35]
            vendor = resolve_authentic_vendor(prod)
            sil = resolve_luxury_bag_silhouette(prod)
            payload = prepare_product_set_payload(prod, forex_rate)
            assert payload.get("title"), f"Missing title for {pid}"
            assert payload.get("vendor"), f"Missing vendor for {pid}"
            assert payload.get("productType") == sil, f"Silhouette mismatch for {pid}"
            assert "Luxury Bags" in payload.get("tags", []), f"Missing Luxury Bags tag for {pid}"
            print(f"[{idx}/{len(candidates)}] [DRY-RUN OK] {vendor:20} | {sil:25} | {title}")
            stats["success"] += 1
        return stats

    start_time = time.time()
    lock = threading.Lock()
    total_count = len(candidates)

    indexed_candidates = [(idx, fp, p) for idx, (fp, p) in enumerate(candidates, 1)]

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(_provision_single_worker, item, forex_rate, stats, lock, total_count, delay)
            for item in indexed_candidates
        ]
        for f in as_completed(futures):
            try:
                f.result()
            except Exception as exc:
                log_error(f"Worker thread exception: {exc}")

    elapsed = time.time() - start_time
    print("=" * 80)
    print(f"PROVISIONING COMPLETE in {elapsed:.1f}s ({elapsed/60:.2f}m)")
    print(f"Total: {stats['total']} | Succeeded: {stats['success']} | Failed: {stats['failed']}")
    print("=" * 80)

    if stats["success"] > 0:
        log_info("Rebuilding centralized catalog index (storage/db/index.json)...")
        try:
            build_and_save_index()
            log_success("Catalog index successfully rebuilt.")
        except Exception as ie:
            log_error(f"Failed to rebuild catalog index: {ie}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Provision Luxury Bags & Leather Goods to Shopify")
    parser.add_argument("--store", type=str, default=None, help="Filter by store: coach, jwpei, michaelkors, or all")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of items to provision")
    parser.add_argument("--dry-run", action="store_true", help="Dry run validation without GraphQL mutation")
    parser.add_argument("--force", action="store_true", help="Force re-provisioning of already synced items")
    parser.add_argument("--delay", type=float, default=0.05, help="Inter-request delay in seconds (default: 0.05)")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent workers (default: 4)")

    args = parser.parse_args()

    run_provisioning(
        store_filter=args.store,
        limit=args.limit,
        dry_run=args.dry_run,
        force=args.force,
        delay=args.delay,
        workers=args.workers
    )


if __name__ == "__main__":
    main()
