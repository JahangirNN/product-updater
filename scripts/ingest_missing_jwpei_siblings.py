"""
JW PEI Missing Sibling Ingestion Script
Ingests all missing sibling colorways (including sold-out ones) into the
partitioned JSON database using the full products.json catalog dump.
Pure functions only, zero classes (ADR 0004, ADR 0005, ADR 0006).
"""
import os
import sys
import json
import time
from typing import Any, Dict, List, Set, Tuple, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from storage.forex import get_usd_to_inr_rate
from storage.validator import validate_product
from storage.db import save_product, build_and_save_index
from stores.jwpei.inflow import parse_product_payload


STARAPPS_JS_PATH = "scratch/starapps_data.js"
ALL_PRODUCTS_JSON_PATH = "scratch/all_jwpei_products.json"
DB_DIR = "storage/db"


def load_starapps_groups(js_path):
    with open(js_path, "r", encoding="utf-8") as f:
        content = f.read()
    prefix = "window.starapps_data.product_groups="
    start_idx = content.find(prefix) + len(prefix)
    depth = 0
    end_idx = -1
    for i in range(start_idx, len(content)):
        if content[i] == "[":
            depth += 1
        elif content[i] == "]":
            depth -= 1
            if depth == 0:
                end_idx = i + 1
                break
    return json.loads(content[start_idx:end_idx])


def load_existing_handles(db_dir):
    handles = set()
    products_dir = os.path.join(db_dir, "jwpei", "products")
    if not os.path.exists(products_dir):
        return handles
    for fname in os.listdir(products_dir):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(products_dir, fname), "r", encoding="utf-8") as f:
                d = json.load(f)
                h = d.get("handle")
                if h:
                    handles.add(h)
        except Exception:
            continue
    return handles


def find_missing_sibling_handles(groups, existing_handles, products_by_handle):
    to_ingest = set()
    for g in groups:
        opts = g.get("option_values", [])
        group_handles = [o["handle"] for o in opts if o.get("handle")]
        if not set(group_handles).intersection(existing_handles):
            continue
        for h in group_handles:
            if h not in existing_handles and h in products_by_handle:
                to_ingest.add(h)
    return sorted(to_ingest)


def price_str_to_cents(price_str):
    """Convert price string (dollars or cents) to integer cents. Returns None if input is None."""
    if price_str is None:
        return None
    try:
        val = float(str(price_str).replace(",", ""))
        if val < 500:
            return int(round(val * 100))
        return int(val)
    except (ValueError, TypeError):
        return None


def convert_products_json_to_js_format(product):
    """
    Convert products.json format to .js endpoint format (prices to integer cents).
    IMPORTANT: Keep top-level price as None when it's missing so inflow.py's
    fallback to first_var.price fires correctly.
    """
    converted = dict(product)
    variants = []
    for v in product.get("variants", []):
        vv = dict(v)
        vv["price"] = price_str_to_cents(v.get("price"))
        vv["compare_at_price"] = price_str_to_cents(v.get("compare_at_price"))
        variants.append(vv)
    converted["variants"] = variants
    # Preserve None so inflow.py falls back to first_var.price
    converted["price"] = price_str_to_cents(product.get("price"))
    converted["compare_at_price"] = price_str_to_cents(product.get("compare_at_price"))
    return converted


def ingest_product_from_catalog(handle, product_data, forex_rate):
    """Parse and save a single product from the products.json catalog."""
    converted = convert_products_json_to_js_format(product_data)
    canonical = parse_product_payload(converted, usd_to_inr_rate=forex_rate, group_name="handbags")
    is_available = any(v.get("available", False) for v in product_data.get("variants", []))
    canonical["availability"] = "in_stock" if is_available else "out_of_stock"
    canonical["is_active"] = is_available
    for v in canonical.get("variants", []):
        v["in_stock"] = is_available
    canonical["shopify_sync_pending"] = False
    is_valid, status, warnings = validate_product(canonical)
    canonical["status"] = status
    canonical["validation_warnings"] = warnings
    saved = save_product(canonical)
    return saved


def run_ingestion():
    print("=" * 70)
    print("JW PEI MISSING SIBLING INGESTION PIPELINE")
    print("=" * 70)

    print("\n[1/5] Loading StarApps swatch groups...")
    groups = load_starapps_groups(STARAPPS_JS_PATH)
    print(f"  Loaded {len(groups)} StarApps product groups")

    print("\n[2/5] Loading JW PEI full catalog (products.json)...")
    with open(ALL_PRODUCTS_JSON_PATH, "r", encoding="utf-8") as f:
        all_products = json.load(f)
    products_by_handle = {p["handle"]: p for p in all_products}
    print(f"  Loaded {len(products_by_handle)} products from full catalog")

    print("\n[3/5] Loading existing DB handles...")
    existing_handles = load_existing_handles(DB_DIR)
    print(f"  Existing products in DB: {len(existing_handles)}")

    print("\n[4/5] Identifying missing siblings in active groups...")
    missing_handles = find_missing_sibling_handles(groups, existing_handles, products_by_handle)
    print(f"  Found {len(missing_handles)} sibling handles to ingest")
    oos_count = sum(
        1 for h in missing_handles
        if not any(v.get("available", False) for v in products_by_handle[h].get("variants", []))
    )
    in_stock_count = len(missing_handles) - oos_count
    print(f"    In-stock: {in_stock_count}, Out-of-stock: {oos_count}")

    print("\n[5/5] Fetching forex rate and ingesting...")
    forex_rate = get_usd_to_inr_rate()
    print(f"  USD->INR rate: Rs.{forex_rate:.4f}")

    ingested = []
    failed = []
    for i, handle in enumerate(missing_handles, 1):
        product_data = products_by_handle[handle]
        is_oos = not any(v.get("available", False) for v in product_data.get("variants", []))
        stock_label = "OOS" if is_oos else "IN_STCK"
        try:
            saved = ingest_product_from_catalog(handle, product_data, forex_rate)
            price_usd = saved.get("source_price", 0)
            price_inr = saved.get("current_price", 0)
            print(f"  [{i:3d}/{len(missing_handles)}] OK [{stock_label}] {handle} | ${price_usd:.2f} -> Rs.{price_inr:.0f}")
            ingested.append({"handle": handle, "id": saved["id"], "availability": saved["availability"], "price_usd": price_usd})
        except Exception as e:
            print(f"  [{i:3d}/{len(missing_handles)}] FAIL {handle}: {e}")
            failed.append({"handle": handle, "error": str(e)})

    print("\n" + "=" * 70)
    print("INGESTION SUMMARY")
    print("=" * 70)
    print(f"  Total missing handles identified:  {len(missing_handles)}")
    print(f"  Successfully ingested:             {len(ingested)}")
    print(f"  Failed:                            {len(failed)}")
    new_in_stock = sum(1 for r in ingested if r["availability"] == "in_stock")
    new_oos = sum(1 for r in ingested if r["availability"] == "out_of_stock")
    print(f"  Newly added in-stock:              {new_in_stock}")
    print(f"  Newly added out-of-stock:          {new_oos}")

    if failed:
        print("\nFailed handles:")
        for f in failed:
            print(f"  - {f['handle']}: {f['error']}")

    print("\nRebuilding DB index...")
    build_and_save_index(DB_DIR)
    print("  Index rebuilt.")
    print("\nDone! Run export_viewer_data.py next.")
    return len(ingested), len(failed)


if __name__ == "__main__":
    run_ingestion()
