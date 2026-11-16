#!/usr/bin/env python3
"""
Ingest unsynced Michael Kors products to Shopify Admin GraphQL via productSet.
Scans storage/db/michaelkors/products/*.json for records without shopify_product_id.
"""
import glob
import json
import os
import sys
import time
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage.shopify_sync import upsert_product_to_shopify
from storage.forex import get_usd_to_inr_rate
from storage.db import _atomic_write_json_with_retry
from storage.logger import log_info, log_success, log_error, log_warning


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    products_dir = os.path.join(base_dir, "storage", "db", "michaelkors", "products")
    
    pattern = os.path.join(products_dir, "*.json")
    all_files = glob.glob(pattern)
    print(f"Total scanned product files in {products_dir}: {len(all_files)}")
    
    unsynced_items = []
    for fpath in sorted(all_files):
        try:
            with open(fpath, "r", encoding="utf-8") as fp:
                prod = json.load(fp)
            if not prod.get("shopify_product_id"):
                unsynced_items.append((fpath, prod))
        except Exception as e:
            print(f"Error reading {fpath}: {e}")
            
    total_unsynced = len(unsynced_items)
    print(f"Found {total_unsynced} unsynced Michael Kors products.")
    
    if total_unsynced == 0:
        print("No unsynced products found. All products are already synced to Shopify.")
        return
        
    forex_rate = get_usd_to_inr_rate()
    print(f"Current USD to INR Forex Rate: {forex_rate:.4f}")
    
    succeeded = []
    failed = []
    
    start_time = time.time()
    
    for idx, (fpath, prod) in enumerate(unsynced_items, 1):
        pid = prod.get("id") or os.path.splitext(os.path.basename(fpath))[0]
        title = prod.get("title", "Unknown Title")
        sku = prod.get("source_sku", "")
        ptype = prod.get("product_type", "")
        
        print(f"[{idx}/{total_unsynced}] Ingesting {pid} | {title[:40]} | SKU: {sku} | Type: {ptype}...")
        
        try:
            success, p_node, err_msg = upsert_product_to_shopify(prod, forex_rate=forex_rate)
            
            if success and p_node and p_node.get("id"):
                gid = p_node["id"]
                variants_count = p_node.get("totalVariants", len(prod.get("variants", [])))
                prod["shopify_product_id"] = gid
                prod["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                
                # Persist updated JSON back to disk atomically
                _atomic_write_json_with_retry(fpath, prod)
                
                succeeded.append({
                    "id": pid,
                    "title": title,
                    "gid": gid,
                    "variants": variants_count
                })
                print(f"  --> SUCCESS: GID={gid} (Variants: {variants_count})")
            else:
                failed.append({
                    "id": pid,
                    "title": title,
                    "error": err_msg or "Unknown error"
                })
                print(f"  --> FAILED: {err_msg}")
        except Exception as ex:
            failed.append({
                "id": pid,
                "title": title,
                "error": str(ex)
            })
            print(f"  --> EXCEPTION: {ex}")
            
        # Polite delay 0.45s between calls (per ADR & prompt instructions)
        time.sleep(0.45)
        
    elapsed = time.time() - start_time
    print("\n" + "="*60)
    print("INGESTION RUN SUMMARY")
    print("="*60)
    print(f"Total Scanned Unsynced: {total_unsynced}")
    print(f"Succeeded: {len(succeeded)}")
    print(f"Failed: {len(failed)}")
    print(f"Elapsed Time: {elapsed:.2f}s (~{elapsed/60:.2f} min)")
    
    if failed:
        print("\nFailed Products:")
        for f_item in failed:
            print(f"  - ID: {f_item['id']} | Title: {f_item['title']} | Error: {f_item['error']}")
    print("="*60)


if __name__ == "__main__":
    main()
