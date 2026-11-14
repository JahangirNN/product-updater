"""
Retry missing or timed-out Sephora products.
Identifies products in sephora_discovered_urls.json that are missing from storage/db/sephora/products/
and attempts ingestion with clean retry logic.
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from storage.forex import get_usd_to_inr_rate
from storage.db import save_product, build_and_save_index
from run_inflow_sephora import fetch_and_parse_sephora_pdp, STORAGE_DB_DIR, DISCOVERED_PATH

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "db")
SEPHORA_PRODS_DIR = os.path.join(DB_DIR, "sephora", "products")


def main():
    with open(DISCOVERED_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    all_prods = manifest.get("products", [])
    
    saved_urls = set()
    if os.path.exists(SEPHORA_PRODS_DIR):
        for fname in os.listdir(SEPHORA_PRODS_DIR):
            if fname.endswith(".json"):
                with open(os.path.join(SEPHORA_PRODS_DIR, fname), "r", encoding="utf-8") as fp:
                    try:
                        p = json.load(fp)
                        u = p.get("source_url")
                        if u:
                            saved_urls.add(u.strip().lower())
                    except Exception:
                        pass

    missing = [p for p in all_prods if p.get("url", "").strip().lower() not in saved_urls]
    print("=" * 80)
    print(f"RETRYING MISSING SEPHORA PRODUCTS: {len(missing)} TO PROCESS")
    print("=" * 80)

    if not missing:
        print("Zero missing products! 100% of discovered products are already ingested.")
        return

    forex_rate = get_usd_to_inr_rate()
    recovered = 0
    failed = 0

    for idx, item in enumerate(missing, 1):
        print(f"[{idx}/{len(missing)}] Retrying: {item.get('brand')} - {item.get('title')[:30]} ({item.get('url')})...")
        canonical = fetch_and_parse_sephora_pdp(item, forex_rate, delay=0.5)
        if canonical:
            save_product(canonical, base_dir=STORAGE_DB_DIR)
            recovered += 1
            print(f"       -> [SUCCESS] Ingested with {len(canonical.get('variants', []))} variants.")
        else:
            failed += 1
            print(f"       -> [FAILED] Could not retrieve PDP.")
        time.sleep(0.5)

    print("=" * 80)
    print(f"RETRY SWEEP COMPLETED: {recovered} recovered, {failed} permanently unavailable/delisted.")
    print("=" * 80)
    build_and_save_index(base_dir=STORAGE_DB_DIR)


if __name__ == "__main__":
    main()
