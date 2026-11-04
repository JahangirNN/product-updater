"""
Sephora Ingestion & Normalization Orchestrator
Reads discovered Sephora products from storage/sephora_discovered_urls.json,
fetches live SSR PDP HTML & Redux hydration JSON via curl_cffi pool,
normalizes with stores.sephora.inflow, and saves atomically to storage/db/sephora/products/.
Pure functions, zero classes (ADR 0004, ADR 0005, ADR 0006).
"""
import os
import sys
import json
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from curl_cffi import requests
from parsel import Selector

from storage.forex import get_usd_to_inr_rate
from storage.db import save_product, build_and_save_index
from stores.sephora.inflow import parse_sephora_payload

DISCOVERED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage", "sephora_discovered_urls.json")
STORAGE_DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage", "db")
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_and_parse_sephora_pdp(
    item_info: Dict[str, Any],
    forex_rate: float,
    delay: float = 0.2
) -> Optional[Dict[str, Any]]:
    """
    Fetch single Sephora PDP, extract SSR Redux page.product JSON, and return canonical product dict.
    Includes 3-attempt backoff retry loop.
    """
    if delay > 0:
        time.sleep(delay)

    url = item_info.get("url")
    brand = item_info.get("brand", "")
    
    if not url:
        return None

    last_err = None
    session = requests.Session(impersonate="chrome124")
    for attempt in range(3):
        try:
            r = session.get(
                url,
                headers=DEFAULT_HEADERS,
                timeout=25,
                allow_redirects=True
            )
            r.encoding = "utf-8"
            if r.status_code != 200 or len(r.text) < 5000:
                last_err = f"HTTP {r.status_code}, len={len(r.text)}"
                time.sleep(1.0 * (attempt + 1))
                continue

            sel = Selector(r.text)
            scripts = sel.css("script::text").getall()
            pdata = None
            for s in scripts:
                s_clean = s.strip()
                if s_clean.startswith('{"page":') and '"product":' in s_clean:
                    try:
                        parsed = json.loads(s_clean)
                        pdata = parsed.get("page", {}).get("product")
                        if pdata:
                            break
                    except Exception:
                        pass

            if not pdata:
                last_err = "No page.product script found"
                time.sleep(1.0 * (attempt + 1))
                continue

            canonical = parse_sephora_payload(
                raw_pdp_json=pdata,
                usd_to_inr_rate=forex_rate,
                default_brand=brand,
                source_url=url
            )
            return canonical

        except Exception as exc:
            last_err = exc
            time.sleep(1.0 * (attempt + 1))

    print(f"[ERROR] Failed {url} after 3 attempts: {last_err}")
    return None


def run_sephora_ingestion(
    brand_filter: Optional[str] = None,
    limit: Optional[int] = None,
    max_workers: int = 4,
    delay: float = 0.25
) -> Dict[str, Any]:
    """Execute concurrent ingestion of Sephora catalog items."""
    if not os.path.exists(DISCOVERED_PATH):
        raise FileNotFoundError(f"Missing {DISCOVERED_PATH}. Please run harvest_sephora_urls.py first.")

    with open(DISCOVERED_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    all_items = manifest.get("products", [])
    if brand_filter:
        b_clean = brand_filter.lower().strip()
        all_items = [p for p in all_items if b_clean in p.get("brand", "").lower()]

    if limit and limit > 0:
        all_items = all_items[:limit]

    total_count = len(all_items)
    forex_rate = get_usd_to_inr_rate()

    print("=" * 80)
    print("SEPHORA CATALOG INGESTION & NORMALIZATION PIPELINE")
    print("=" * 80)
    print(f"Total Target Products : {total_count}")
    print(f"Target Brand Filter    : {brand_filter or 'ALL 14 BRANDS'}")
    print(f"Forex Conversion Rate  : 1 USD = ₹{forex_rate:.2f}")
    print(f"Worker Concurrency     : {max_workers} threads (jitter delay {delay}s)")
    print("=" * 80)

    saved_count = 0
    errors_count = 0
    total_variants_saved = 0
    brand_stats: Dict[str, Dict[str, int]] = {}

    t0_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_item = {
            executor.submit(fetch_and_parse_sephora_pdp, item, forex_rate, delay): item
            for item in all_items
        }

        for idx, future in enumerate(as_completed(future_to_item), 1):
            item = future_to_item[future]
            brand = item.get("brand", "Unknown")
            if brand not in brand_stats:
                brand_stats[brand] = {"saved": 0, "variants": 0, "in_stock": 0, "oos": 0, "errors": 0}

            try:
                canonical = future.result()
                if canonical:
                    # Save atomically to storage/db/sephora/products/{product_id}.json
                    saved = save_product(canonical, base_dir=STORAGE_DB_DIR)
                    saved_count += 1
                    
                    v_list = saved.get("variants", [])
                    v_len = len(v_list)
                    total_variants_saved += v_len
                    
                    is_in_stock = (saved.get("availability") == "in_stock")
                    brand_stats[brand]["saved"] += 1
                    brand_stats[brand]["variants"] += v_len
                    if is_in_stock:
                        brand_stats[brand]["in_stock"] += 1
                    else:
                        brand_stats[brand]["oos"] += 1

                    if idx % 10 == 0 or idx == total_count:
                        pct = (idx / total_count) * 100
                        elapsed = time.perf_counter() - t0_start
                        rate = idx / elapsed if elapsed > 0 else 0
                        print(f"[{idx:>3}/{total_count}] ({pct:>5.1f}%) Saved: {saved_count} | Variants: {total_variants_saved} | Rate: {rate:.1f} prod/s")
                else:
                    errors_count += 1
                    brand_stats[brand]["errors"] += 1
                    print(f"[{idx:>3}/{total_count}] [FAIL] {item.get('title', 'Unknown')[:30]} ({item.get('url')})")
            except Exception as exc:
                errors_count += 1
                brand_stats[brand]["errors"] += 1
                print(f"[{idx:>3}/{total_count}] [EXCEPTION] {exc}")

    elapsed_total = time.perf_counter() - t0_start

    print("\n" + "=" * 80)
    print("UPDATING UNIFIED CATALOG INDEX (storage/db/index.json)...")
    index_manifest = build_and_save_index(base_dir=STORAGE_DB_DIR)
    print(f"SUCCESS: Unified index updated. Total catalog items: {len(index_manifest)}")
    print("=" * 80)

    print("\n" + "=" * 80)
    print(f"{'BRAND':<20} | {'SAVED':<6} | {'VARIANTS':<9} | {'IN-STOCK':<9} | {'OOS':<5} | {'ERRORS':<6}")
    print("-" * 80)
    for b_name, s in sorted(brand_stats.items()):
        print(f"{b_name:<20} | {s['saved']:<6} | {s['variants']:<9} | {s['in_stock']:<9} | {s['oos']:<5} | {s['errors']:<6}")
    print("-" * 80)
    print(f"{'TOTAL':<20} | {saved_count:<6} | {total_variants_saved:<9} | {'-':<9} | {'-':<5} | {errors_count:<6}")
    print(f"Elapsed Time: {elapsed_total:.2f} seconds ({elapsed_total/60:.2f} minutes)")
    print("=" * 80)

    return {
        "total_targets": total_count,
        "saved_count": saved_count,
        "errors_count": errors_count,
        "total_variants": total_variants_saved,
        "brand_stats": brand_stats,
        "elapsed_seconds": elapsed_total
    }


def main():
    parser = argparse.ArgumentParser(description="Sephora Product Inflow Ingestion")
    parser.add_argument("--brand", type=str, default=None, help="Filter to single brand name")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of products to ingest")
    parser.add_argument("--workers", type=int, default=4, help="Number of concurrent worker threads")
    parser.add_argument("--delay", type=float, default=0.2, help="Delay between requests in seconds")
    args = parser.parse_args()

    run_sephora_ingestion(
        brand_filter=args.brand,
        limit=args.limit,
        max_workers=args.workers,
        delay=args.delay
    )


if __name__ == "__main__":
    main()
