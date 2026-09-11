"""
Michael Kors Ingestion Script
Iterates through all discovered products in scratch/mk_discovered_catalog.json,
normalizes them using stores.michaelkors.inflow, and saves them atomically into storage/db/michaelkors/products/.
Pure functions only, zero classes (ADR 0004, ADR 0005).
"""
import os
import json
import time
from storage.forex import get_usd_to_inr_rate
from storage.db import save_product
from stores.michaelkors.inflow import normalize_canonical_product

def run_michaelkors_ingestion():
    catalog_path = "scratch/mk_discovered_catalog.json"
    if not os.path.exists(catalog_path):
        raise FileNotFoundError(f"Catalog file not found: {catalog_path}")

    with open(catalog_path, "r", encoding="utf-8") as f:
        raw_catalog = json.load(f)

    print(f"Loaded {len(raw_catalog)} unique discovered products from {catalog_path}")
    forex_rate = get_usd_to_inr_rate()
    print(f"Current USD -> INR forex rate: {forex_rate:.4f}")

    saved_count = 0
    errors = 0
    by_category = {}

    start_time = time.time()
    for sku, raw_item in raw_catalog.items():
        try:
            canonical = normalize_canonical_product(raw_item, forex_rate)
            saved = save_product(canonical)
            saved_count += 1
            cat = canonical.get("product_type", "Other")
            by_category[cat] = by_category.get(cat, 0) + 1
        except Exception as err:
            errors += 1
            print(f"[ERROR] Failed to normalize/save SKU {sku}: {err}")

    elapsed = time.time() - start_time
    print("========================================================================")
    print("MICHAEL KORS INGESTION COMPLETE")
    print("========================================================================")
    print(f"Total Products Ingested: {saved_count}")
    print(f"Errors Encountered:      {errors}")
    print(f"Ingestion Duration:      {elapsed:.2f} seconds")
    print("\nBreakdown by Category:")
    for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
        print(f"  - {cat:<15}: {count}")
    print("========================================================================")

if __name__ == "__main__":
    run_michaelkors_ingestion()
