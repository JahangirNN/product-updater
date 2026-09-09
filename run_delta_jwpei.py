"""
JW PEI Handbags Full Delta Verification Harness (Data Freshner)
Rapidly polls price and stock status across all ingested products.
Pure functions, zero classes (ADR 0002, ADR 0004, ADR 0005).
"""
import os
import sys
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List
import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from storage.db import build_and_save_index, append_delta_log, load_product, save_product
from stores.jwpei.delta import check_price_and_stock

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


def poll_product_worker(item: Dict[str, Any], client: httpx.Client) -> Dict[str, Any]:
    """Worker function to check single product delta with polite pacing."""
    res = check_price_and_stock(item, client=client)
    time.sleep(0.08)
    return res


def run_full_delta(max_workers: int = 3):
    print("=" * 70)
    print("JW PEI CATALOG DELTA FRESHNER (STOCK & PRICE MONITOR)")
    print("=" * 70)

    # 1. Load products from index
    index_file = "storage/db/index.json"
    if not os.path.exists(index_file):
        print(f"Error: {index_file} not found. Run ingestion first.")
        return

    with open(index_file, "r", encoding="utf-8") as f:
        catalog_index = json.load(f)

    # Filter jwpei products
    items = [val for val in catalog_index.values() if val.get("store") == "jwpei"]
    total = len(items)
    print(f"Loaded {total} JW PEI products for live status & price check.")

    start_time = time.time()
    deltas = []
    latencies = []
    price_shifts = 0
    stock_shifts = 0
    in_stock_count = 0
    out_stock_count = 0
    errors = 0

    print(f"\nStarting concurrent delta scan with {max_workers} worker threads...")

    with httpx.Client(headers=HEADERS, timeout=httpx.Timeout(6.0, connect=3.0)) as client:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_item = {
                executor.submit(poll_product_worker, item, client): item
                for item in items
            }

            completed = 0
            for future in as_completed(future_to_item):
                completed += 1
                orig_item = future_to_item[future]
                res = future.result()
                if not res or not isinstance(res, dict):
                    errors += 1
                    continue

                latencies.append(res.get("elapsed_ms", 0))

                if res.get("status") == "error":
                    errors += 1
                elif res.get("status") in ("success", "not_found"):
                    if res.get("availability") == "in_stock":
                        in_stock_count += 1
                    else:
                        out_stock_count += 1

                    if res.get("price_changed"):
                        price_shifts += 1
                        print(f"  [PRICE CHANGE] {res['handle']}: ${res['old_source_price']} -> ${res['current_source_price']}")

                    if res.get("stock_changed"):
                        stock_shifts += 1
                        print(f"  [STOCK CHANGE] {res['handle']}: {res['old_availability']} -> {res['availability']}")

                if completed % 50 == 0 or completed == total:
                    print(f"[{completed:3d}/{total}] Checked: {res.get('handle', '')[:30]} | {res.get('availability')} | {res.get('elapsed_ms')}ms")

    total_time = time.time() - start_time
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    # 2. Record batch run to history ledger
    summary_entry = {
        "action": "batch_delta_scan",
        "store": "jwpei",
        "products_checked": total,
        "in_stock": in_stock_count,
        "out_of_stock": out_stock_count,
        "price_changes_detected": price_shifts,
        "stock_changes_detected": stock_shifts,
        "errors": errors,
        "average_latency_ms": round(avg_latency, 2),
        "total_time_seconds": round(total_time, 2)
    }
    append_delta_log(summary_entry)

    print("\n" + "=" * 70)
    print("DELTA FRESHNER SCAN RESULTS")
    print("=" * 70)
    print(f"Total Products Checked:    {total}")
    print(f"Currently In Stock:        {in_stock_count}")
    print(f"Currently Out of Stock:    {out_stock_count}")
    print(f"Price Changes Detected:    {price_shifts}")
    print(f"Stock Changes Detected:    {stock_shifts}")
    print(f"Failed / Request Errors:   {errors}")
    print(f"Average Request Latency:   {avg_latency:.2f} ms")
    print(f"Total Scan Duration:       {total_time:.2f} seconds ({total_time/total*1000:.1f} ms/product throughput)")
    print("Logged to storage/db/history/delta_log.json")
    print("=" * 70)


if __name__ == "__main__":
    run_full_delta(max_workers=3)
