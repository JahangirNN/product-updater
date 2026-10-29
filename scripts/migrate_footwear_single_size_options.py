"""
Live Shopify Footwear Single-Size Options Migration Script
Restructures footwear products across JD Sports, Foot Locker, and Nordstrom on Shopify Admin GraphQL.
Collapses dual Size (US) & Size (UK) options into single unified 'Size' option with pure UK values.
Zero Cartesian combinatorial deadlocks. Preserves handles, URLs, images, and prices.
Supports multi-worker pacing (ThreadPoolExecutor) and pending-item resumption.
Adheres to ADR 0002, 0005, 0006, 0019, 0020, 0021, and 0024.
"""
import os
import sys
import glob
import json
import time
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from storage.shopify_auth import execute_shopify_graphql
from storage.shopify_taxonomy import prepare_product_set_payload
from storage.forex import get_usd_to_inr_rate
from storage.logger import log_info, log_success, log_warning, log_error

PRODUCT_SET_MUTATION = """
mutation productSet($input: ProductSetInput!, $synchronous: Boolean!) {
  productSet(input: $input, synchronous: $synchronous) {
    product {
      id
      title
      handle
      status
      totalVariants
      onlineStoreUrl
      options {
        id
        name
        values
      }
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

_PRINT_LOCK = threading.Lock()
_DISK_LOCK = threading.Lock()


def load_footwear_products(
    store_filter: Optional[str] = None,
    pending_only: bool = True
) -> List[Tuple[str, Dict[str, Any]]]:
    """Load local JSON product files for target footwear stores."""
    db_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "db")
    stores = [store_filter] if store_filter and store_filter != "all" else ["jdsports", "footlocker", "nordstrom"]

    products = []
    for s in stores:
        pattern = os.path.join(db_root, s, "products", "*.json")
        for fp in sorted(glob.glob(pattern)):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    prod = json.load(f)
                if pending_only and prod.get("shopify_sync_pending") is False:
                    continue
                products.append((fp, prod))
            except Exception as exc:
                log_error(f"Failed to read {fp}: {exc}")

    return products


def migrate_single_product_to_shopify(
    file_path: str,
    prod: Dict[str, Any],
    forex_rate: float,
    dry_run: bool = False
) -> Tuple[bool, str]:
    """
    Push restructured single-size option schema to Shopify via productSet.
    Updates local file on success.
    """
    shopify_id = prod.get("shopify_product_id")
    handle = prod.get("handle") or prod.get("shopify_handle")

    if not shopify_id:
        return False, f"Missing shopify_product_id for {handle}"

    payload = prepare_product_set_payload(prod, forex_rate)
    payload["id"] = shopify_id

    # Defensive check: ensure no dual size dimensions in payload options
    opt_names = [o.get("name") for o in payload.get("productOptions", [])]
    if "Size (US)" in opt_names and "Size (UK)" in opt_names:
        return False, f"Dual size options still detected in payload: {opt_names}"

    if dry_run:
        return True, f"DryRun Validated: options={opt_names}, variants={len(payload.get('variants', []))}"

    # Execute GraphQL productSet mutation with retry on rate limit
    for attempt in range(4):
        data, ext, err = execute_shopify_graphql(
            PRODUCT_SET_MUTATION,
            variables={"input": payload, "synchronous": True}
        )

        if err:
            err_str = str(err).lower()
            if "throttled" in err_str or "429" in err_str or "cost" in err_str:
                time.sleep(1.5 * (attempt + 1))
                continue
            return False, f"GraphQL Error: {err}"

        if not data:
            return False, "Empty GraphQL response"

        res = data.get("productSet", {})
        u_errors = res.get("userErrors", [])
        if u_errors:
            err_msg = "; ".join(f"{e.get('field')}: {e.get('message')}" for e in u_errors)
            if "throttled" in err_msg.lower():
                time.sleep(1.5 * (attempt + 1))
                continue
            return False, f"UserErrors: {err_msg}"

        # Success: Stamp local JSON record thread-safely
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        prod["shopify_synced_at"] = now_iso
        prod["shopify_sync_pending"] = False
        with _DISK_LOCK:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(prod, f, indent=2, ensure_ascii=False)
            except Exception as f_err:
                log_warning(f"Failed to update file {file_path}: {f_err}")

        p_node = res.get("product") or {}
        new_opts = [o.get("name") for o in p_node.get("options", [])]
        return True, f"Success (Shopify options: {new_opts}, totalVariants: {p_node.get('totalVariants')})"

    return False, "Exceeded retry attempts due to throttling"


def run_shopify_migration(
    store_filter: Optional[str] = None,
    limit: Optional[int] = None,
    dry_run: bool = False,
    workers: int = 3,
    delay: float = 0.25,
    force: bool = False
) -> Dict[str, Any]:
    """
    Run throttled batch migration of footwear products to Shopify Admin.
    """
    print("=" * 80)
    print(f"LIVE SHOPIFY FOOTWEAR SINGLE-SIZE OPTIONS MIGRATION")
    print(f"Store: {store_filter or 'ALL'} | Limit: {limit or 'ALL'} | DryRun: {dry_run} | Workers: {workers} | Force: {force}")
    print("=" * 80)

    forex_rate = get_usd_to_inr_rate()
    log_info(f"Active Forex Rate: 1 USD = INR {forex_rate:.2f}")

    products = load_footwear_products(store_filter, pending_only=not force)
    log_info(f"Found {len(products)} candidate products eligible for migration.")

    if limit and limit > 0:
        products = products[:limit]
        log_info(f"Limit applied: processing first {len(products)} products.")

    stats = {
        "total": len(products),
        "success": 0,
        "failed": 0
    }

    if not products:
        log_success("All footwear products are already migrated and synchronized!")
        return stats

    t0 = time.time()
    counter_lock = threading.Lock()
    processed_count = [0]

    def _worker_task(item_tuple: Tuple[str, Dict[str, Any]]) -> Tuple[bool, str, str, str]:
        fp, prod = item_tuple
        store_name = prod.get("source_store", "unknown")
        handle = prod.get("handle") or prod.get("shopify_handle") or str(prod.get("id"))

        ok, msg = migrate_single_product_to_shopify(
            file_path=fp,
            prod=prod,
            forex_rate=forex_rate,
            dry_run=dry_run
        )
        if not dry_run and delay > 0:
            time.sleep(delay)
        return ok, msg, store_name, handle

    if workers <= 1:
        for idx, item in enumerate(products, 1):
            ok, msg, store_name, handle = _worker_task(item)
            if ok:
                stats["success"] += 1
                log_info(f"[{idx:4d}/{len(products):4d}] [{store_name[:4].upper()}] {handle[:32]:32s} | OK: {msg}")
            else:
                stats["failed"] += 1
                log_error(f"[{idx:4d}/{len(products):4d}] [{store_name[:4].upper()}] {handle[:32]:32s} | FAILED: {msg}")
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_item = {executor.submit(_worker_task, item): item for item in products}
            for future in as_completed(future_to_item):
                with counter_lock:
                    processed_count[0] += 1
                    current_idx = processed_count[0]

                try:
                    ok, msg, store_name, handle = future.result()
                    with _PRINT_LOCK:
                        if ok:
                            stats["success"] += 1
                            log_info(f"[{current_idx:4d}/{len(products):4d}] [{store_name[:4].upper()}] {handle[:32]:32s} | OK: {msg}")
                        else:
                            stats["failed"] += 1
                            log_error(f"[{current_idx:4d}/{len(products):4d}] [{store_name[:4].upper()}] {handle[:32]:32s} | FAILED: {msg}")
                except Exception as exc:
                    with _PRINT_LOCK:
                        stats["failed"] += 1
                        log_error(f"[{current_idx:4d}/{len(products):4d}] Task unhandled exception: {exc}")

    duration = time.time() - t0
    print("=" * 80)
    print(f"SHOPIFY MIGRATION COMPLETE | Processed: {stats['total']} | Succeeded: {stats['success']} | Failed: {stats['failed']} | Duration: {duration:.1f}s")
    print("=" * 80)
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate footwear products to single Size option on Shopify.")
    parser.add_argument("--store", type=str, default=None, help="Filter store: jdsports, footlocker, nordstrom, all")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of products to process")
    parser.add_argument("--dry-run", action="store_true", help="Validate payloads without mutating Shopify")
    parser.add_argument("--workers", type=int, default=3, help="Number of concurrent worker threads (default: 3)")
    parser.add_argument("--delay", type=float, default=0.25, help="Delay in seconds between requests per worker (default: 0.25s)")
    parser.add_argument("--force", action="store_true", help="Force migration even if already synced")
    args = parser.parse_args()

    run_shopify_migration(
        store_filter=args.store,
        limit=args.limit,
        dry_run=args.dry_run,
        workers=args.workers,
        delay=args.delay,
        force=args.force
    )
