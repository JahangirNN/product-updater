"""
JW PEI Handbags Full Ingestion Pipeline
Ingests all 288 discovered filtered handbag products into the partitioned JSON database.
Uses the single-endpoint architecture with polite pacing and exponential backoff on 429.
Pure functions, zero classes (ADR 0004, ADR 0005, ADR 0006).
"""
import os
import sys
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Tuple, Optional
import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from storage.forex import get_usd_to_inr_rate
from storage.validator import validate_product
from storage.db import save_product, build_and_save_index
from stores.jwpei.inflow import parse_product_payload

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}


def fetch_product_with_backoff(handle: str, client: httpx.Client, max_retries: int = 4) -> Tuple[str, Dict[str, Any], Optional[str]]:
    """
    Fetch /products/{handle}.js with exponential backoff on 429 rate limiting.
    Returns (handle, data_dict, error_message).
    """
    url = f"https://www.jwpei.com/products/{handle}.js"
    backoff = 1.5

    for attempt in range(max_retries):
        try:
            resp = client.get(url, timeout=12.0)
            if resp.status_code == 429:
                time.sleep(backoff)
                backoff *= 2.0
                continue
            if resp.status_code == 404:
                return handle, {}, "HTTP 404 (Delisted/Not Found)"
            resp.raise_for_status()
            data = resp.json()
            time.sleep(0.08)  # Polite pacing delay
            return handle, data, None
        except Exception as err:
            if attempt == max_retries - 1:
                return handle, {}, str(err)
            time.sleep(backoff)
            backoff *= 1.5

    return handle, {}, "Max retries exceeded (HTTP 429)"


def process_and_save_product(handle: str, raw_data: Dict[str, Any], forex_rate: float) -> Dict[str, Any]:
    """Parse, validate, and save product record."""
    canonical = parse_product_payload(raw_data, usd_to_inr_rate=forex_rate, group_name="handbags")
    is_valid, status, warnings = validate_product(canonical)
    canonical["status"] = status
    canonical["validation_warnings"] = warnings
    
    saved = save_product(canonical)
    return {
        "handle": handle,
        "id": saved["id"],
        "title": saved["title"],
        "sku": saved["source_sku"],
        "price_usd": saved["source_price"],
        "price_inr": saved["current_price"],
        "availability": saved["availability"],
        "status": status,
        "images_count": len(saved["images"]),
        "has_specs": len(saved["specifications"]) > 0
    }


def run_full_inflow(max_workers: int = 3):
    print("=" * 70)
    print("JW PEI FULL CATALOG INGESTION (HANDBAGS <= $150 USD)")
    print("=" * 70)

    # 1. Load discovered handles
    handles_file = "scratch/all_handles.json"
    if not os.path.exists(handles_file):
        print(f"Error: {handles_file} not found. Run discovery first.")
        return

    with open(handles_file, "r", encoding="utf-8") as f:
        handles = json.load(f)

    total = len(handles)
    print(f"Loaded {total} unique handles for ingestion.")

    # 2. Get live exchange rate
    forex_rate = get_usd_to_inr_rate()
    print(f"USD -> INR Exchange Rate: ₹{forex_rate:.4f} (Cached 24h)")

    start_time = time.time()
    results = []
    failed = []

    print(f"\nStarting polite concurrent ingestion with {max_workers} worker threads...")

    with httpx.Client(headers=HEADERS) as client:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_handle = {
                executor.submit(fetch_product_with_backoff, handle, client): handle
                for handle in handles
            }

            completed_count = 0
            for future in as_completed(future_to_handle):
                completed_count += 1
                handle, raw_data, err = future.result()

                if err:
                    failed.append({"handle": handle, "error": err})
                    print(f"[{completed_count:3d}/{total}] FAIL: {handle} -> {err}")
                    continue

                try:
                    summary = process_and_save_product(handle, raw_data, forex_rate)
                    results.append(summary)
                    if completed_count % 20 == 0 or completed_count == total:
                        print(f"[{completed_count:3d}/{total}] Ingested: {summary['title'][:35]} | ₹{summary['price_inr']:,.0f} | {summary['availability']} | {summary['status']}")
                except Exception as parse_err:
                    failed.append({"handle": handle, "error": str(parse_err)})
                    print(f"[{completed_count:3d}/{total}] PARSE ERROR: {handle} -> {parse_err}")

    # 3. Rebuild global index
    print("\nUpdating storage/db/index.json...")
    index_map = build_and_save_index()

    total_time = time.time() - start_time
    active_count = sum(1 for r in results if r["status"] == "ACTIVE")
    draft_count = sum(1 for r in results if r["status"] == "DRAFT")
    in_stock_count = sum(1 for r in results if r["availability"] == "in_stock")
    out_stock_count = sum(1 for r in results if r["availability"] == "out_of_stock")

    print("\n" + "=" * 70)
    print("INGESTION SUMMARY")
    print("=" * 70)
    print(f"Total Products Processed: {completed_count}/{total}")
    print(f"Successfully Saved:       {len(results)}")
    print(f"Failed / Errors:          {len(failed)}")
    print(f"Active Listings:          {active_count}")
    print(f"Draft Listings:           {draft_count}")
    print(f"In Stock:                 {in_stock_count}")
    print(f"Out of Stock:             {out_stock_count}")
    print(f"Total Index Size:         {len(index_map)} items")
    print(f"Total Time Taken:         {total_time:.2f} seconds ({total_time/total:.2f}s per product)")
    print("=" * 70)


if __name__ == "__main__":
    run_full_inflow(max_workers=3)
