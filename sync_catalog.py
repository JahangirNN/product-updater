"""
Global Catalog Sync & Delta Freshner Engine
Systematically polls live retailer endpoints to monitor stock availability and price shifts.
Orchestrates multi-store updates with polite concurrency and logs deltas for Shopify syncing.
Pure functions only, zero classes (ADR 0002, ADR 0004, ADR 0005, ADR 0006).
"""
import os
import sys
import json
import time
import argparse
import importlib
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple
import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from storage.db import (
    load_product,
    save_product,
    build_and_save_index,
    append_delta_log,
    append_delta_event
)
from storage.forex import get_usd_to_inr_rate
from storage.logger import (
    init_logger,
    log_info,
    log_success,
    log_warning,
    log_error,
    log_delta
)

DEFAULT_CONFIG_PATH = "config/delta_config.json"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


def load_delta_config(config_path: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """Load centralized delta configuration or provide resilient defaults."""
    cfg = {
        "check_interval_minutes": 60,
        "default_max_workers": 3,
        "default_delay_seconds": 0.08,
        "default_timeout_seconds": 6.0,
        "store_configs": {},
        "shopify_sync": {
            "auto_sync_on_delta": False,
            "queue_file": "storage/db/history/delta_events.json"
        },
        "logging": {
            "log_dir": "logs",
            "general_log": "freshner.log",
            "error_log": "errors.log",
            "rotation_general": "20 MB",
            "rotation_error": "10 MB",
            "retention_general": "14 days",
            "retention_error": "30 days",
            "console_level": "INFO"
        }
    }
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                cfg.update(loaded)
        except Exception as err:
            log_warning(f"Failed to read {config_path}: {err}. Using defaults.")

    log_cfg = cfg.get("logging", {})
    init_logger(
        log_dir=log_cfg.get("log_dir", "logs"),
        general_log_name=log_cfg.get("general_log", "freshner.log"),
        error_log_name=log_cfg.get("error_log", "errors.log"),
        rotation_general=log_cfg.get("rotation_general", "20 MB"),
        rotation_error=log_cfg.get("rotation_error", "10 MB"),
        retention_general=log_cfg.get("retention_general", "14 days"),
        retention_error=log_cfg.get("retention_error", "30 days"),
        console_level=log_cfg.get("console_level", "INFO")
    )
    return cfg


def parse_iso_timestamp(ts_str: Optional[str]) -> Optional[float]:
    """Parse ISO 8601 UTC timestamp to epoch seconds."""
    if not ts_str:
        return None
    try:
        dt = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt.timestamp()
    except Exception:
        return None


def is_product_due(product: Dict[str, Any], interval_minutes: float, force: bool = False) -> Tuple[bool, float]:
    """
    Check if a product is due for a delta check based on last_verified_at.
    Returns (is_due, elapsed_minutes).
    """
    if force:
        return True, 999999.0

    last_ts = parse_iso_timestamp(product.get("last_verified_at"))
    if not last_ts:
        return True, 999999.0

    now_epoch = time.time()
    elapsed_minutes = (now_epoch - last_ts) / 60.0
    return (elapsed_minutes >= interval_minutes), elapsed_minutes


def resolve_store_delta_module(store_name: str) -> Optional[Any]:
    """Dynamically import stores/{store_name}/delta.py."""
    module_path = f"stores.{store_name}.delta"
    try:
        mod = importlib.import_module(module_path)
        if hasattr(mod, "check_price_and_stock") and hasattr(mod, "apply_delta_to_product"):
            return mod
        log_warning(f"Module {module_path} is missing required delta functions.")
        return None
    except ModuleNotFoundError:
        log_warning(f"No delta module found for store '{store_name}' at {module_path}.")
        return None


def poll_single_product(
    product_stub: Dict[str, Any],
    store_mod: Any,
    client: httpx.Client,
    forex_rate: float,
    delay_seconds: float,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Worker function to check single product delta, mutate if needed, and return result.
    """
    store = product_stub.get("store") or product_stub.get("source_store")
    p_id = product_stub.get("id")

    full_product = load_product(store, p_id)
    if not full_product:
        return {
            "status": "error",
            "id": p_id,
            "error": f"Product file {p_id} not found on disk."
        }

    # Execute store delta check
    delta_res = store_mod.check_price_and_stock(full_product, client=client)
    time.sleep(delay_seconds)

    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Apply delta to product model
    updated_product, has_changed = store_mod.apply_delta_to_product(full_product, delta_res, forex_rate)

    if not dry_run:
        # Save mutated product (or touched timestamp) to disk
        save_product(updated_product)

        if has_changed:
            # Enqueue event for Shopify sync
            event_entry = {
                "event_id": f"evt_{int(time.time()*1000)}_{p_id[:8]}",
                "timestamp": now_iso,
                "store": store,
                "product_id": p_id,
                "handle": updated_product.get("handle"),
                "title": updated_product.get("title"),
                "price_changed": delta_res.get("price_changed", False),
                "old_source_price": delta_res.get("old_source_price"),
                "new_source_price": delta_res.get("current_source_price"),
                "new_current_price_inr": updated_product.get("current_price"),
                "stock_changed": delta_res.get("stock_changed", False),
                "old_availability": delta_res.get("old_availability"),
                "new_availability": delta_res.get("availability"),
                "shopify_sync_pending": True
            }
            append_delta_event(event_entry)

    delta_res["id"] = p_id
    delta_res["store"] = store
    delta_res["has_changed"] = has_changed
    return delta_res


def run_catalog_sync(
    interval_override: Optional[float] = None,
    store_filter: Optional[str] = None,
    force: bool = False,
    limit: Optional[int] = None,
    dry_run: bool = False,
    config_path: str = DEFAULT_CONFIG_PATH
) -> Dict[str, Any]:
    """
    Run systematic catalog delta sync across all products and stores.
    """
    log_info("=" * 72)
    log_info("GLOBAL DROPSHIP CATALOG SYNC & DELTA FRESHNER")
    log_info("=" * 72)

    config = load_delta_config(config_path)
    base_interval = interval_override if interval_override is not None else config.get("check_interval_minutes", 60)

    log_info(f"Active Check Interval: {base_interval:.1f} minutes {'[OVERRIDE]' if interval_override else ''}")
    log_info(f"Force Mode:            {force}")
    log_info(f"Dry Run:               {dry_run}")
    if store_filter:
        log_info(f"Target Store:          {store_filter}")

    # 1. Load catalog index
    index_file = "storage/db/index.json"
    if not os.path.exists(index_file):
        log_info("Rebuilding storage index...")
        catalog_index = build_and_save_index()
    else:
        with open(index_file, "r", encoding="utf-8") as f:
            catalog_index = json.load(f)

    all_products = list(catalog_index.values())
    log_info(f"Total Products in DB:  {len(all_products)}")

    # 2. Filter by store
    if store_filter:
        all_products = [p for p in all_products if (p.get("store") == store_filter or p.get("source_store") == store_filter)]

    # 3. Filter due products
    due_products = []
    skipped_count = 0
    for p in all_products:
        store_name = p.get("store") or p.get("source_store", "default")
        store_conf = config.get("store_configs", {}).get(store_name, {})
        store_interval = interval_override if interval_override is not None else store_conf.get("check_interval_minutes", base_interval)
        
        is_due, elapsed = is_product_due(p, store_interval, force=force)
        if is_due:
            due_products.append((p, store_interval))
        else:
            skipped_count += 1

    log_info(f"Products Due for Sync: {len(due_products)}")
    log_info(f"Products Skipped:      {skipped_count} (checked within last {base_interval:.1f}m)")

    if limit and limit > 0:
        due_products = due_products[:limit]
        log_info(f"Limit Applied:         Processing first {len(due_products)} products")

    if not due_products:
        log_success("All products are fresh. No delta polling needed.")
        log_info("=" * 72)
        return {"scanned": 0, "skipped": skipped_count, "price_changes": 0, "stock_changes": 0}

    # 4. Resolve store modules & fetch forex
    forex_rate = get_usd_to_inr_rate()
    log_info(f"Forex Rate Cached:     1 USD = ₹{forex_rate:.2f}")

    start_time = time.time()
    latencies = []
    price_shifts = 0
    stock_shifts = 0
    in_stock_count = 0
    out_stock_count = 0
    errors = 0

    # Group due products by store to apply per-store concurrency
    by_store: Dict[str, List[Dict[str, Any]]] = {}
    for p, _ in due_products:
        s = p.get("store") or p.get("source_store", "default")
        by_store.setdefault(s, []).append(p)

    total_due = len(due_products)
    completed = 0

    for store_name, store_items in by_store.items():
        store_mod = resolve_store_delta_module(store_name)
        if not store_mod:
            log_warning(f"[SKIP] Skipping {len(store_items)} items for unsupported store '{store_name}'.")
            continue

        store_conf = config.get("store_configs", {}).get(store_name, {})
        max_workers = store_conf.get("max_workers", config.get("default_max_workers", 3))
        delay_sec = store_conf.get("delay_seconds", config.get("default_delay_seconds", 0.08))
        timeout_sec = store_conf.get("timeout_seconds", config.get("default_timeout_seconds", 6.0))

        log_info(f"Checking {len(store_items)} products for '{store_name}' (workers={max_workers}, delay={delay_sec}s)")

        with httpx.Client(headers=DEFAULT_HEADERS, timeout=httpx.Timeout(timeout_sec, connect=3.0)) as client:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_item = {
                    executor.submit(
                        poll_single_product,
                        item,
                        store_mod,
                        client,
                        forex_rate,
                        delay_sec,
                        dry_run
                    ): item
                    for item in store_items
                }

                for future in as_completed(future_to_item):
                    completed += 1
                    res = future.result()
                    if not res or not isinstance(res, dict):
                        errors += 1
                        log_error(f"Received invalid result for product {future_to_item[future].get('id')}")
                        continue

                    latencies.append(res.get("elapsed_ms", 0))

                    if res.get("status") == "error":
                        errors += 1
                        log_error(f"Sync error for {res.get('handle', res.get('id'))}: {res.get('error')}")
                    elif res.get("status") in ("success", "not_found"):
                        avail = res.get("availability")
                        if avail == "in_stock":
                            in_stock_count += 1
                        else:
                            out_stock_count += 1

                        if res.get("price_changed"):
                            price_shifts += 1
                            log_delta("PRICE", res.get('handle', 'unknown'), f"${res.get('old_source_price')} -> ${res.get('current_source_price')} USD")

                        if res.get("stock_changed"):
                            stock_shifts += 1
                            log_delta("STOCK", res.get('handle', 'unknown'), f"{res.get('old_availability')} -> {avail}")

                    if completed % 25 == 0 or completed == total_due:
                        log_info(f"[{completed:3d}/{total_due}] Progress: {res.get('handle', '')[:32]} | {res.get('availability', 'unknown')} | {res.get('elapsed_ms', 0)}ms")

    total_time = time.time() - start_time
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    # 5. Rebuild index if changes written
    if not dry_run:
        build_and_save_index()

        summary_log = {
            "action": "global_delta_sync",
            "interval_minutes": base_interval,
            "force": force,
            "products_checked": completed,
            "products_skipped": skipped_count,
            "in_stock": in_stock_count,
            "out_of_stock": out_stock_count,
            "price_changes": price_shifts,
            "stock_changes": stock_shifts,
            "errors": errors,
            "average_latency_ms": round(avg_latency, 2),
            "total_time_seconds": round(total_time, 2)
        }
        append_delta_log(summary_log)

    log_success("=" * 72)
    log_success("CATALOG SYNC COMPLETE")
    log_success("=" * 72)
    log_info(f"Products Checked:          {completed}")
    log_info(f"Products Skipped:          {skipped_count}")
    log_info(f"Currently In Stock:        {in_stock_count}")
    log_info(f"Currently Out of Stock:    {out_stock_count}")
    log_info(f"Price Shifts Detected:     {price_shifts}")
    log_info(f"Stock Shifts Detected:     {stock_shifts}")
    if errors > 0:
        log_error(f"Failed / Request Errors:   {errors} (check logs/errors.log for diagnostics)")
    else:
        log_info(f"Failed / Request Errors:   {errors}")
    log_info(f"Average Request Latency:   {avg_latency:.2f} ms")
    log_info(f"Total Sweep Duration:      {total_time:.2f} seconds")
    if not dry_run:
        log_info("Logged to storage/db/history/delta_log.json")
        if price_shifts > 0 or stock_shifts > 0:
            log_info("Events queued in storage/db/history/delta_events.json (ready for Shopify sync)")
    log_info("=" * 72)

    return {
        "scanned": completed,
        "skipped": skipped_count,
        "in_stock": in_stock_count,
        "out_of_stock": out_stock_count,
        "price_changes": price_shifts,
        "stock_changes": stock_shifts,
        "errors": errors,
        "duration_seconds": total_time
    }


def main():
    parser = argparse.ArgumentParser(description="Dropship Catalog Live Delta Freshner & Sync Engine")
    parser.add_argument("--interval", type=float, help="Override check interval in minutes (e.g. 2 for testing, 120 for normal)")
    parser.add_argument("--store", type=str, help="Target specific store (e.g. jwpei)")
    parser.add_argument("--force", action="store_true", help="Force check all products bypassing last_verified_at")
    parser.add_argument("--limit", type=int, help="Limit number of checked products")
    parser.add_argument("--dry-run", action="store_true", help="Inspect live status without writing mutations to disk")
    parser.add_argument("--config", type=str, default=DEFAULT_CONFIG_PATH, help="Path to delta config JSON")

    args = parser.parse_args()

    run_catalog_sync(
        interval_override=args.interval,
        store_filter=args.store,
        force=args.force,
        limit=args.limit,
        dry_run=args.dry_run,
        config_path=args.config
    )


if __name__ == "__main__":
    main()
