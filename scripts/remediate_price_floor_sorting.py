"""
Remediation Script: Synchronize OOS Variant Price Floors to Eliminate Sort Inversions
Iterates through all local store products, finds products where OOS variants have cheaper
prices than the minimum in-stock variant, and pushes updated productSet payloads to Shopify.
Adheres to ADR 0005, 0006, 0015, 0021.
"""
import os
import sys
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.shopify_sync import upsert_product_to_shopify
from storage.forex import get_usd_to_inr_rate
from storage.logger import log_info, log_success, log_error, log_warning

def find_discrepancy_products() -> List[Dict[str, Any]]:
    db_dir = "storage/db"
    stores = ["jdsports", "coach", "footlocker", "nordstrom", "michaelkors", "jwpei", "jomashop"]
    forex_rate = get_usd_to_inr_rate()
    
    target_products = []
    
    for s in stores:
        p_dir = os.path.join(db_dir, s, "products")
        if not os.path.exists(p_dir):
            continue
        for fname in os.listdir(p_dir):
            if not fname.endswith('.json'):
                continue
            fpath = os.path.join(p_dir, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    shopify_id = data.get("shopify_product_id")
                    if not shopify_id:
                        continue
                    
                    # Delisted products already set to DRAFT, skip
                    if data.get("supplier_delisted") or data.get("availability") != "in_stock":
                        continue
                        
                    variants = data.get("variants", [])
                    if len(variants) <= 1:
                        continue
                        
                    in_stock_prices = []
                    oos_prices = []
                    
                    for v in variants:
                        p = float(v.get("source_price") or data.get("source_price") or 0.0)
                        if p <= 0:
                            continue
                        in_inr = round(p * forex_rate)
                        if v.get("in_stock") is True or v.get("availability") == "in_stock":
                            in_stock_prices.append(in_inr)
                        else:
                            oos_prices.append(in_inr)
                            
                    if in_stock_prices and oos_prices:
                        min_in_stock = min(in_stock_prices)
                        min_oos = min(oos_prices)
                        if min_oos < min_in_stock:
                            target_products.append({
                                "file_path": fpath,
                                "product": data,
                                "store": s,
                                "min_in_stock": min_in_stock,
                                "min_oos": min_oos,
                                "diff": min_in_stock - min_oos
                            })
            except Exception:
                pass
                
    return target_products

def run_remediation(max_workers: int = 5, limit: int = None):
    targets = find_discrepancy_products()
    print(f"Total products identified with OOS price floor discrepancy: {len(targets)}")
    if limit:
        targets = targets[:limit]
        print(f"Limiting execution to first {limit} products.")
        
    forex_rate = get_usd_to_inr_rate()
    success_count = 0
    fail_count = 0
    
    def _worker(item):
        prod = item["product"]
        handle = prod.get("handle")
        shopify_id = prod.get("shopify_product_id")
        try:
            ok, p_node, err = upsert_product_to_shopify(prod, forex_rate)
            if ok:
                # Also synchronize local DB variant prices for OOS variants to match floor
                for v in prod.get("variants", []):
                    if not (v.get("in_stock") is True or v.get("availability") == "in_stock"):
                        v_p = float(v.get("source_price") or prod.get("source_price") or 0.0)
                        if round(v_p * forex_rate) < item["min_in_stock"]:
                            v["price"] = f"{float(item['min_in_stock']):.2f}"
                            v["price_current"] = float(item["min_in_stock"])
                from storage.db import save_product
                save_product(prod)
                return True, handle, f"Floor adjusted: Rs. {item['min_oos']} -> Rs. {item['min_in_stock']}"
            else:
                return False, handle, err
        except Exception as exc:
            return False, handle, str(exc)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_item = {executor.submit(_worker, it): it for it in targets}
        for future in as_completed(future_to_item):
            it = future_to_item[future]
            ok, handle, msg = future.result()
            if ok:
                success_count += 1
                print(f"[{success_count + fail_count}/{len(targets)}] SUCCESS: {handle[:35]} | {msg}")
            else:
                fail_count += 1
                print(f"[{success_count + fail_count}/{len(targets)}] FAILED:  {handle[:35]} | {msg}")
                
    print("\n" + "="*80)
    print(f"Remediation Finished: {success_count} succeeded, {fail_count} failed out of {len(targets)} total.")
    print("="*80)

if __name__ == "__main__":
    run_remediation(max_workers=5)
