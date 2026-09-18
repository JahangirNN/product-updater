"""
Foot Locker Nike Vomero Collection Ingestion Pipeline
Scrapes and ingests Nike Vomero footwear from Foot Locker into the partitioned JSON database.
Enforces zero 1-size truncation invariant, separates widths from numeric sizes,
formats whole-rupee INR prices, and persists atomically to storage/db/footlocker/products/.
Pure functions only, zero classes (ADR 0004, ADR 0005, ADR 0006).
"""
import os
import sys
import re
import json
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Tuple
import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from storage.forex import get_usd_to_inr_rate
from storage.validator import validate_product
from storage.db import save_product, build_and_save_index
from stores.footlocker.inflow import parse_product_payload

CACHE_DIR = "scratch/fl_raw_pdp"
HARVESTED_FILE = "scratch/harvested_102.json"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}


def fetch_and_extract_pdp(sku: str, title: str, client: httpx.Client) -> Optional[Dict[str, Any]]:
    """
    Fetch PDP HTML and extract hydrated data and high-res images.
    Caches raw extraction to disk for instant zero-latency re-runs.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, f"{sku}.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    slug = re.sub(r'[^a-zA-Z0-9]+', '-', title.lower()).strip('-')
    pdp_url = f"https://www.footlocker.com/product/{slug}/{sku}.html"

    for attempt in range(3):
        try:
            r = client.get(pdp_url, headers=HEADERS, follow_redirects=True, timeout=25.0)
            if r.status_code == 404:
                print(f"  [404] Product {sku} delisted or not found at {pdp_url}")
                return None
            if r.status_code != 200:
                time.sleep(1.0)
                continue

            html = r.text
            idx = html.find('STATE_FROM_SERVER:')
            if idx == -1:
                print(f"  [WARN] No STATE_FROM_SERVER in {sku} PDP")
                return None

            d, _ = json.JSONDecoder().raw_decode(html[idx + len('STATE_FROM_SERVER:'):].lstrip())
            data = d.get('api', {}).get('productDetails', {}).get('getDetails', {}).get('data', {})
            if not data:
                print(f"  [WARN] Empty getDetails.data in {sku} PDP")
                return None

            # Extract high-res images from JSON-LD
            images = []
            json_lds = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
            for jld in json_lds:
                try:
                    jd = json.loads(jld)
                    if jd.get('@type') == 'ProductGroup' and 'hasVariant' in jd:
                        for var in jd['hasVariant']:
                            if var.get('sku') == sku:
                                v_img = var.get('image', [])
                                if isinstance(v_img, list): images.extend(v_img)
                                elif isinstance(v_img, str): images.append(v_img)
                    elif jd.get('@type') == 'Product' and 'image' in jd:
                        p_img = jd['image']
                        if isinstance(p_img, list): images.extend(p_img)
                        elif isinstance(p_img, str): images.append(p_img)
                except Exception:
                    pass

            data['images'] = images
            data['pdp_url'] = pdp_url

            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f)

            return data
        except Exception as e:
            if attempt == 2:
                print(f"  [ERROR] Failed to fetch {sku}: {e}")
                return None
            time.sleep(1.0)
    return None


def run_footlocker_ingestion(max_workers: int = 4) -> int:
    print("=" * 72)
    print("FOOT LOCKER NIKE VOMERO COLLECTION INGESTION")
    print("=" * 72)

    if not os.path.exists(HARVESTED_FILE):
        raise FileNotFoundError(f"Harvested catalog file not found: {HARVESTED_FILE}")

    with open(HARVESTED_FILE, "r", encoding="utf-8") as f:
        discovered = json.load(f)

    print(f"Discovered products ready for PDP ingestion: {len(discovered)}")
    forex_rate = get_usd_to_inr_rate()
    print(f"Live USD -> INR Forex Rate: ₹{forex_rate:.2f}")

    products_to_fetch = []
    for item in discovered:
        sku = item.get('sku')
        name = item.get('name') or "Nike Vomero"
        if sku:
            products_to_fetch.append((sku, name))

    print(f"Fetching and parsing {len(products_to_fetch)} product detail pages...")

    success_count = 0
    truncated_count = 0
    skipped_count = 0
    in_stock_count = 0
    out_of_stock_count = 0

    with httpx.Client() as client:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_sku = {
                executor.submit(fetch_and_extract_pdp, sku, name, client): (sku, name)
                for sku, name in products_to_fetch
            }

            for future in as_completed(future_to_sku):
                sku, name = future_to_sku[future]
                try:
                    raw_data = future.result()
                    if not raw_data:
                        skipped_count += 1
                        continue

                    canonical = parse_product_payload(raw_data, forex_rate=forex_rate)
                    if not canonical:
                        print(f"  [SKIP] {sku} failed normalizer (truncated or invalid).")
                        skipped_count += 1
                        continue

                    # Strict Quality Invariant Verification
                    variants = canonical.get("variants", [])
                    if len(variants) <= 1:
                        print(f"  [FATAL TRUNCATION] {sku} has only {len(variants)} variant!")
                        truncated_count += 1
                        continue

                    is_valid, status, warnings = validate_product(canonical)
                    if not is_valid:
                        print(f"  [VALIDATION ERROR] {sku}: {warnings}")
                        skipped_count += 1
                        continue

                    # Atomic persistence
                    save_product(canonical)
                    success_count += 1

                    if canonical.get("availability") == "in_stock":
                        in_stock_count += 1
                    else:
                        out_of_stock_count += 1

                    print(f"  [SAVED] {sku:10s} | {canonical['title'][:30]:30s} | {len(variants):2d} sizes | ₹{canonical['current_price']:.0f} | {canonical['availability']}")

                except Exception as exc:
                    print(f"  [ERROR] {sku} unhandled exception: {exc}")
                    skipped_count += 1

    # Build and persist partition index
    print("\nBuilding store partition index...")
    build_and_save_index("footlocker")

    print("\n" + "=" * 72)
    print("FOOT LOCKER INGESTION REPORT")
    print("=" * 72)
    print(f"Total Products Ingested  : {success_count}")
    print(f"In-Stock Products        : {in_stock_count}")
    print(f"Out-of-Stock Products    : {out_of_stock_count}")
    print(f"Truncated (<= 1 variant) : {truncated_count} (Invariant Target: 0)")
    print(f"Skipped / Errors         : {skipped_count}")
    print("=" * 72)

    assert truncated_count == 0, f"Violation of anti-truncation invariant: {truncated_count} truncated items!"
    assert success_count >= 90, f"Expected at least 90 products, got {success_count}"
    return success_count


if __name__ == "__main__":
    run_footlocker_ingestion()
