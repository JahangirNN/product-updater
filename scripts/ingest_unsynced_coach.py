"""
Coach Unsynced Products Ingestion Script
Ingests all unsynced COACH products (Footwear, Wallets, Bags) into Shopify via Admin GraphQL productSet.
Adheres to ADR 0005, 0006, 0015, 0019, 0020, 0021.
"""
import os
import sys
import json
import time
from typing import Dict, Any, List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from storage.shopify_sync import upsert_product_to_shopify
from storage.forex import get_usd_to_inr_rate
from storage.db import _atomic_write_json_with_retry, build_and_save_index
from storage.logger import log_info, log_success, log_error, log_shopify_error, log_shopify_success


def run_ingest(delay_seconds: float = 0.45):
    print("=" * 80)
    print("STARTING COACH SHOPIFY INGESTION PIPELINE")
    print("=" * 80)

    db_dir = os.path.join(PROJECT_ROOT, "storage", "db", "coach", "products")
    if not os.path.exists(db_dir):
        print(f"Error: Directory {db_dir} does not exist.")
        return

    all_files = [os.path.join(db_dir, f) for f in os.listdir(db_dir) if f.endswith(".json")]
    total_scanned = len(all_files)
    print(f"Total COACH product records scanned: {total_scanned}")

    unsynced_items = []
    already_synced_count = 0

    for fpath in all_files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                prod = json.load(f)
        except Exception as e:
            print(f"Error reading {fpath}: {e}")
            continue

        sp_id = prod.get("shopify_product_id")
        if not sp_id or not str(sp_id).strip():
            unsynced_items.append((fpath, prod))
        else:
            already_synced_count += 1

    print(f"Already synced in Shopify: {already_synced_count}")
    print(f"Identified unsynced records: {len(unsynced_items)}")

    if not unsynced_items:
        print("No unsynced products found. Everything is up to date!")
        return

    forex_rate = get_usd_to_inr_rate()
    print(f"Active USD/INR Forex rate: {forex_rate:.4f}")
    print(f"Polite delay between items: {delay_seconds:.2f}s")
    print("-" * 80)

    succeeded = []
    failed = []

    total_to_process = len(unsynced_items)

    for idx, (fpath, prod) in enumerate(unsynced_items, start=1):
        pid = prod.get("id") or os.path.basename(fpath).replace(".json", "")
        title = prod.get("title", "")[:35]
        cat = prod.get("source_category") or prod.get("product_type") or "Footwear/Accessories"

        print(f"[{idx}/{total_to_process}] Ingesting: {pid} | {title} ({cat})...", end=" ", flush=True)

        try:
            ok, p_node, err = upsert_product_to_shopify(prod, forex_rate)
        except Exception as ex:
            ok = False
            p_node = None
            err = str(ex)

        if ok and p_node:
            shop_id = p_node.get("id")
            handle = p_node.get("handle")

            # Persist Shopify attributes atomically back to disk
            prod["shopify_product_id"] = shop_id
            prod["shopify_handle"] = handle
            prod["shopify_synced_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            prod["shopify_sync_pending"] = False

            try:
                _atomic_write_json_with_retry(fpath, prod)
                succeeded.append({"id": pid, "title": title, "shopify_id": shop_id, "handle": handle})
                print(f"SUCCESS -> {shop_id}")
            except Exception as se:
                print(f"STAMP ERROR -> {se}")
                failed.append({"id": pid, "title": title, "error": f"Disk write failed: {se}"})
        else:
            print(f"FAILED -> {err}")
            failed.append({"id": pid, "title": title, "error": err})

        if idx < total_to_process and delay_seconds > 0:
            time.sleep(delay_seconds)

    print("-" * 80)
    print("Rebuilding central index.json...")
    try:
        build_and_save_index()
        print("Index successfully updated.")
    except Exception as ie:
        print(f"Warning: Index rebuild failed: {ie}")

    print("=" * 80)
    print("INGESTION BATCH SUMMARY")
    print("=" * 80)
    print(f"Total Coach scanned:       {total_scanned}")
    print(f"Processed in this run:     {total_to_process}")
    print(f"Succeeded in this run:     {len(succeeded)}")
    print(f"Failed in this run:        {len(failed)}")

    if failed:
        print("\nFailed Product IDs:")
        for item in failed:
            print(f"  - ID: {item['id']} | Title: {item['title']} | Error: {item['error']}")
    else:
        print("\nAll products in this run ingested with 100% success!")

    return {
        "total_scanned": total_scanned,
        "processed": total_to_process,
        "succeeded": len(succeeded),
        "failed": len(failed),
        "failed_items": failed,
    }


if __name__ == "__main__":
    run_ingest(delay_seconds=0.45)
