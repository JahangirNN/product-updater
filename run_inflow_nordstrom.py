"""
Nordstrom On Shoes Full Ingestion Pipeline
Ingests discovered On Running shoes from Nordstrom into the partitioned JSON database.
Enforces strict filter: ONLY products that offer at least 7 distinct size variants (len(size_variants) >= 7).
Stores all available sizes with appropriate UK sizes alongside US sizes using the official On size conversion matrix.
Pure functions, zero classes (ADR 0004, ADR 0005, ADR 0006).
"""
import os
import sys
import json
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Tuple, Optional
import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from storage.forex import get_usd_to_inr_rate
from storage.validator import validate_product
from storage.db import save_product, build_and_save_index
from stores.nordstrom.inflow import parse_product_payload

FIRECRAWL_API_URL = "https://api.firecrawl.dev/v1/scrape"
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY", "fc-c8760028c40942e685a271b9a4067238")
CACHE_DIR = "scratch/nordstrom_raw"

FIRECRAWL_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "brand": {"type": "string"},
        "gender": {"type": "string", "enum": ["men", "women", "unisex", "kids"]},
        "current_price": {"type": "number"},
        "regular_price": {"type": "number"},
        "colors": {
            "type": "array",
            "items": {"type": "string"}
        },
        "sizes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "us_size": {"type": "string"},
                    "uk_size": {"type": "string"},
                    "eu_size": {"type": "string"},
                    "in_stock": {"type": "boolean"}
                },
                "required": ["us_size"]
            }
        },
        "images": {
            "type": "array",
            "items": {"type": "string"}
        },
        "details": {
            "type": "object",
            "properties": {
                "midsole_drop": {"type": "string"},
                "materials": {"type": "string"},
                "cushioning": {"type": "string"},
                "item_number": {"type": "string"},
                "style_id": {"type": "string"}
            }
        }
    },
    "required": ["title", "current_price", "sizes"]
}


def get_cache_path(url: str) -> str:
    """Get deterministic cache file path for a URL."""
    url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
    return os.path.join(CACHE_DIR, f"{url_hash}.json")


def fetch_product_via_firecrawl(
    url: str,
    client: httpx.Client,
    max_retries: int = 3
) -> Tuple[str, Dict[str, Any], Optional[str]]:
    """
    Fetch and extract structured product payload from Nordstrom PDP via Firecrawl.
    Checks local disk cache first for zero-credit instant re-runs.
    """
    cache_file = get_cache_path(url)
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
            return url, cached_data, None
        except Exception:
            pass

    headers = {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "url": url,
        "formats": ["json"],
        "jsonOptions": {
            "prompt": "Extract product title, brand, gender (men, women, unisex, kids), current sale price, regular/original price, colors list, all sizes with their US size, UK size, EU size, and stock availability, high-res images, and performance details.",
            "schema": FIRECRAWL_SCHEMA
        }
    }

    import random
    backoff = 4.0
    for attempt in range(max_retries):
        try:
            resp = client.post(FIRECRAWL_API_URL, headers=headers, json=payload, timeout=90.0)
            if resp.status_code == 429:
                wait_sec = backoff + random.uniform(1.0, 3.0)
                time.sleep(wait_sec)
                backoff *= 1.5
                continue
            if resp.status_code == 404:
                return url, {}, "HTTP 404 (Not Found)"
            resp.raise_for_status()
            data = resp.json()
            extracted = data.get("data", {}).get("json", {})
            if not extracted and "data" in data:
                extracted = data["data"]

            # Cache response atomically
            os.makedirs(CACHE_DIR, exist_ok=True)
            tmp_cache = f"{cache_file}.tmp"
            with open(tmp_cache, "w", encoding="utf-8") as f:
                json.dump(extracted, f, indent=2)
            os.replace(tmp_cache, cache_file)

            time.sleep(0.4)  # Polite pacing
            return url, extracted, None
        except Exception as err:
            if attempt == max_retries - 1:
                return url, {}, str(err)
            time.sleep(backoff + random.uniform(1.0, 2.0))
            backoff *= 1.5

    return url, {}, "Max retries exceeded"


import re
from scripts.export_viewer_data import export_catalog


def process_and_save_product(
    url: str,
    raw_data: Dict[str, Any],
    forex_rate: float,
    min_size_variants: int = 7,
    min_us_size: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    """
    Parse raw payload, enforce min 7 size variants filter, validate, and save product.
    Returns summary dict if product accepted; returns None if excluded.
    """
    raw_data["url"] = url
    canonical = parse_product_payload(
        raw_data,
        usd_to_inr_rate=forex_rate,
        group_name="shoes",
        min_size_variants=min_size_variants,
        min_us_size=min_us_size
    )
    if not canonical:
        # Excluded by size filter (e.g. < 7 distinct size variants or kids category leak)
        return None

    is_valid, status, warnings = validate_product(canonical)
    canonical["status"] = status
    canonical["validation_warnings"] = warnings
    canonical.setdefault("last_verified_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    saved = save_product(canonical)

    # Extract min and max sizes safely
    sizes_list = []
    for v in saved.get("variants", []):
        for opt in v.get("option_values", []):
            if "size (us)" in opt.get("option_name", "").lower():
                m = re.search(r'(\d+(?:\.\d+)?)', opt.get("name", ""))
                if m:
                    sizes_list.append(float(m.group(1)))
                    break

    min_size_val = min(sizes_list) if sizes_list else 0.0
    max_size_val = max(sizes_list) if sizes_list else 0.0

    return {
        "url": url,
        "id": saved["id"],
        "title": saved["title"],
        "sku": saved["source_sku"],
        "vendor": saved["vendor"],
        "price_usd": saved["source_price"],
        "price_inr": saved["current_price"],
        "availability": saved["availability"],
        "status": status,
        "variants_count": len(saved["variants"]),
        "images_count": len(saved["images"]),
        "has_size_guide": "<details class=\"size-guide-accordion\"" in saved.get("descriptionHtml", ""),
        "min_size": min_size_val,
        "max_size": max_size_val
    }


def run_full_inflow(max_workers: int = 3, min_size_variants: int = 7):
    print("=" * 75)
    print("NORDSTROM ON SHOES CATALOG INGESTION (X-MODE TIER 1)")
    print(f"Filter Constraint: Distinct Size Variants >= {min_size_variants} | Storing All Available US & UK Sizes")
    print("=" * 75)

    # Clear previous Nordstrom product files to remove items excluded under the corrected filter
    nordstrom_dir = "storage/db/nordstrom/products"
    if os.path.exists(nordstrom_dir):
        print(f"Purging existing products in {nordstrom_dir} for clean ingestion...")
        for old_file in os.listdir(nordstrom_dir):
            if old_file.endswith(".json"):
                try:
                    os.remove(os.path.join(nordstrom_dir, old_file))
                except Exception:
                    pass

    os.makedirs(CACHE_DIR, exist_ok=True)

    urls_file = "scratch/all_nordstrom_urls.json"
    if not os.path.exists(urls_file):
        print(f"Error: {urls_file} not found. Run discovery first.")
        return

    with open(urls_file, "r", encoding="utf-8") as f:
        urls = json.load(f)

    total = len(urls)
    print(f"Loaded {total} unique Nordstrom On shoe URLs for ingestion.")

    forex_rate = get_usd_to_inr_rate()
    print(f"USD -> INR Exchange Rate: ₹{forex_rate:.4f} (Cached 24h)")

    start_time = time.time()
    results: List[Dict[str, Any]] = []
    excluded: List[str] = []
    failed: List[Dict[str, Any]] = []

    print(f"\nStarting polite concurrent ingestion with {max_workers} worker threads...")

    with httpx.Client() as client:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {
                executor.submit(fetch_product_via_firecrawl, url, client): url
                for url in urls
            }

            completed_count = 0
            for future in as_completed(future_to_url):
                completed_count += 1
                url, raw_data, err = future.result()

                if err:
                    failed.append({"url": url, "error": err})
                    print(f"[{completed_count:3d}/{total}] FAIL: {url.split('/')[-2]} -> {err}")
                    continue

                try:
                    summary = process_and_save_product(
                        url, raw_data, forex_rate, min_size_variants=min_size_variants
                    )
                    if summary:
                        results.append(summary)
                        print(f"[{completed_count:3d}/{total}] INGESTED: {summary['title'][:32]:<32} | ₹{summary['price_inr']:>6,.0f} | US {summary['min_size']:g}-{summary['max_size']:g} ({summary['variants_count']} sizes) | {summary['status']}", flush=True)
                    else:
                        excluded.append(url)
                        print(f"[{completed_count:3d}/{total}] EXCLUDED (< {min_size_variants} sizes/kids): {url.split('/')[-2]}", flush=True)
                except Exception as parse_err:
                    failed.append({"url": url, "error": str(parse_err)})
                    print(f"[{completed_count:3d}/{total}] PARSE ERROR: {url.split('/')[-2]} -> {parse_err}", flush=True)

    # Rebuild index.json
    print("\nUpdating storage/db/index.json...")
    index_map = build_and_save_index()

    # Rebuild frontend viewer catalog data
    print("Exporting updated catalog bundle for frontend viewer...")
    export_catalog()

    total_time = time.time() - start_time
    active_count = sum(1 for r in results if r["status"] == "ACTIVE")
    draft_count = sum(1 for r in results if r["status"] == "DRAFT")
    in_stock_count = sum(1 for r in results if r["availability"] == "in_stock")
    out_stock_count = sum(1 for r in results if r["availability"] == "out_of_stock")

    print("\n" + "=" * 75)
    print("INGESTION SUMMARY")
    print("=" * 75)
    print(f"Total Discovered URLs:            {total}")
    print(f"Ingested (>= {min_size_variants} Size Variants):      {len(results)}")
    print(f"Excluded (< {min_size_variants} Sizes / Kids):       {len(excluded)}")
    print(f"Failed / Scrape Errors:           {len(failed)}")
    print(f"Active Listings:                  {active_count}")
    print(f"Draft Listings:                   {draft_count}")
    print(f"In Stock:                         {in_stock_count}")
    print(f"Out of Stock:                     {out_stock_count}")
    print(f"Total Global Index:               {len(index_map)} items")
    print(f"Total Time Taken:                 {total_time:.2f}s")
    print("=" * 75)


if __name__ == "__main__":
    run_full_inflow(max_workers=2, min_size_variants=7)
