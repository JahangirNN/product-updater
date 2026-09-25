"""
Shopify High-Throughput Bulk Catalog Ingestor & Store Onboarder
Ingests catalog products across all stores into Shopify Admin via productSet GraphQL.
Supports polite throttling, dry-run payload verification, idempotent disk stamping,
and automatic index rebuilding.
Adheres to ADR 0005, 0006, 0015, 0019, 0020, and 0021.
"""
import os
import sys
import glob
import json
import time
import argparse
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from storage.shopify_sync import upsert_product_to_shopify
from storage.shopify_taxonomy import prepare_product_set_payload, resolve_authentic_vendor
from storage.shopify_collections import provision_all_collections
from storage.forex import get_usd_to_inr_rate
from storage.db import build_and_save_index
from storage.logger import log_info, log_success, log_warning, log_error


def load_candidate_products(store: Optional[str] = None, category: Optional[str] = None, force: bool = False) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Load candidate product files from storage/db partitioned directories.
    Filters out already-synced products unless --force is set.
    """
    db_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "db")
    
    if store and store.lower() != "all":
        pattern = os.path.join(db_root, store, "products", "*.json")
        file_paths = glob.glob(pattern)
    else:
        file_paths = glob.glob(os.path.join(db_root, "*", "products", "*.json"))

    candidates = []
    for fp in file_paths:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                prod = json.load(f)

            # Skip if already uploaded and not force
            if prod.get("shopify_product_id") and not force:
                continue

            # Category filter if provided
            if category:
                pt = str(prod.get("product_type", "")).lower()
                cat_lower = category.lower()
                tags = [t.lower() for t in prod.get("tags", [])]
                if cat_lower not in pt and not any(cat_lower in t for t in tags):
                    continue

            candidates.append((fp, prod))
        except Exception:
            pass

    return candidates


def run_bulk_upload(
    store: Optional[str] = None,
    category: Optional[str] = None,
    limit: Optional[int] = None,
    dry_run: bool = False,
    force: bool = False,
    delay: float = 0.3
) -> Dict[str, Any]:
    """
    Execute high-throughput bulk ingestion to Shopify.
    """
    print("=" * 80)
    print(f"SHOPIFY BULK UPLOADER | Store: {store or 'all'} | Category: {category or 'all'} | DryRun: {dry_run}")
    print("=" * 80)

    forex_rate = get_usd_to_inr_rate()
    log_info(f"Using live forex rate: 1 USD = INR {forex_rate:.2f}")

    candidates = load_candidate_products(store=store, category=category, force=force)
    log_info(f"Loaded {len(candidates)} candidate products eligible for upload.")

    if limit and limit > 0:
        candidates = candidates[:limit]
        log_info(f"Applying limit: processing first {len(candidates)} items.")

    if not candidates:
        log_warning("No candidate products found matching the criteria.")
        return {"total": 0, "success": 0, "failed": 0, "skipped": 0}

    stats = {
        "total": len(candidates),
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "errors": []
    }

    start_time = time.time()

    for idx, (fpath, prod) in enumerate(candidates, 1):
        p_id = prod.get("id") or os.path.basename(fpath).replace(".json", "")
        p_title = prod.get("title", "")[:40]
        vendor = resolve_authentic_vendor(prod)

        if dry_run:
            payload = prepare_product_set_payload(prod, forex_rate)
            # Verify payload invariants
            assert payload.get("title"), "Missing title"
            assert payload.get("vendor"), "Missing vendor"
            assert payload.get("variants"), "Missing variants"
            
            # Check for retailer leaks
            for leak in ["jomashop", "nordstrom", "footlocker", "finishline", "jdsports"]:
                assert leak not in payload["vendor"].lower(), f"Vendor leak: {payload['vendor']}"
                for t in payload.get("tags", []):
                    assert leak not in t.lower(), f"Tag leak: {t}"

            print(f"[{idx}/{len(candidates)}] [DRY-RUN OK] {vendor} | {payload['productType']} | {p_title} | Variants: {len(payload['variants'])}")
            stats["success"] += 1
            continue

        # Real upload
        print(f"[{idx}/{len(candidates)}] Ingesting '{p_title}' ({vendor})...", end=" ", flush=True)
        ok, p_node, err = upsert_product_to_shopify(prod, forex_rate)

        if ok and p_node:
            shop_id = p_node.get("id")
            handle = p_node.get("handle")
            print(f"SUCCESS -> {shop_id} ({handle})")
            
            # Stamp product file on disk
            prod["shopify_product_id"] = shop_id
            prod["shopify_handle"] = handle
            prod["shopify_synced_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            prod["shopify_sync_pending"] = False

            try:
                with open(fpath, "w", encoding="utf-8") as pf:
                    json.dump(prod, pf, indent=2, ensure_ascii=False)
            except Exception as se:
                log_error(f"Failed to stamp product file {fpath}: {se}")

            stats["success"] += 1
        else:
            print(f"FAILED -> {err}")
            stats["failed"] += 1
            stats["errors"].append({"id": p_id, "title": p_title, "error": err})

        time.sleep(delay)

    elapsed = time.time() - start_time
    print("=" * 80)
    print(f"BULK INGESTION COMPLETE in {elapsed:.1f}s")
    print(f"Total Processed: {stats['total']} | Succeeded: {stats['success']} | Failed: {stats['failed']}")
    print("=" * 80)

    if not dry_run and stats["success"] > 0:
        log_info("Rebuilding centralized catalog index (storage/db/index.json)...")
        try:
            build_and_save_index()
            log_success("Catalog index successfully rebuilt.")
        except Exception as ie:
            log_error(f"Failed to rebuild index: {ie}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Shopify High-Throughput Bulk Catalog Ingestor")
    parser.add_argument("--store", type=str, default=None, help="Filter by store (jwpei, coach, michaelkors, nordstrom, footlocker, jdsports, all)")
    parser.add_argument("--category", type=str, default=None, help="Filter by category (e.g. Handbags, Footwear, Watches)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of items to upload")
    parser.add_argument("--dry-run", action="store_true", help="Validate taxonomy and payloads without sending GraphQL requests")
    parser.add_argument("--force", action="store_true", help="Force re-upload of already synced products")
    parser.add_argument("--delay", type=float, default=0.3, help="Inter-request delay in seconds (default 0.3s)")
    parser.add_argument("--provision-collections", action="store_true", help="Provision all smart collections before starting upload")

    args = parser.parse_args()

    if args.provision_collections:
        provision_all_collections()

    run_bulk_upload(
        store=args.store,
        category=args.category,
        limit=args.limit,
        dry_run=args.dry_run,
        force=args.force,
        delay=args.delay
    )


if __name__ == "__main__":
    main()
