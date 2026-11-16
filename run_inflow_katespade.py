"""
Kate Spade Outlet Ingestion & Normalization Script
Reads 429 discovered URLs from storage/katespade_discovered_urls.json,
fetches high-fidelity PDP HTML and JSON-LD via HTTP pool,
normalizes with stores.katespade.inflow, and saves atomically to storage/db/katespade/products/.
Pure functions, zero classes (ADR 0004, ADR 0005, ADR 0006).
"""
import os
import sys
import json
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from curl_cffi import requests
from parsel import Selector

from storage.forex import get_usd_to_inr_rate
from storage.db import save_product, build_and_save_index
from stores.katespade.inflow import parse_product_payload

DISCOVERED_URLS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage", "katespade_discovered_urls.json")
DEFAULT_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
}


def fetch_and_parse_pdp(url: str, forex_rate: float, delay: float = 0.2) -> Optional[Dict[str, Any]]:
    """Fetch single Kate Spade PDP, extract rich JSON-LD and DOM specs, and return canonical product."""
    if delay > 0:
        time.sleep(delay)

    t0 = time.perf_counter()
    try:
        r = requests.get(url, headers=DEFAULT_HEADERS, impersonate="chrome124", timeout=25, allow_redirects=True)
        if r.status_code != 200 or len(r.text) < 1000:
            print(f"[WARN] Failed fetch for {url}: status {r.status_code}, length {len(r.text)}")
            return None

        sel = Selector(r.text)

        # 1. Parse JSON-LD blocks
        json_ld_list = sel.css('script[type="application/ld+json"]::text').getall()
        product_group = None
        product_obj = None

        for jld in json_ld_list:
            try:
                data = json.loads(jld)
                if isinstance(data, dict):
                    if data.get("@type") == "ProductGroup":
                        product_group = data
                    elif data.get("@type") == "Product":
                        product_obj = data
            except Exception:
                pass

        # 2. Extract DOM bullets & specs
        bullets = []
        for li in sel.css('.product-props__details li, .pdp-specs li, .product-description li'):
            t = li.xpath('string(.)').get()
            if t and t.strip():
                bullets.append(t.strip())

        if not bullets:
            for text in sel.css('.product-props__details *::text').getall():
                t = text.strip()
                if t and len(t) > 2 and not t.startswith('.'):
                    bullets.append(t)

        # 3. Base Identity
        title = sel.css('h1::text, .product-name::text, title::text').get() or ""
        title = title.split("|")[0].strip()

        # SKU from URL or JSON-LD
        sku_match = re.search(r'/([A-Z0-9]+-[A-Z0-9]+)\.html', url, re.IGNORECASE)
        sku = sku_match.group(1).upper() if sku_match else (product_obj.get("sku") if product_obj else "KS-UNKNOWN")

        offers = (product_obj.get("offers") or {}) if product_obj else {}
        if isinstance(offers, list) and offers:
            offers = offers[0]
        source_price = float(offers.get("price") or 0.0)

        # Compare at price from DOM if present
        compare_at_text = sel.css('.price-standard::text, .strike-through::text, .was-price::text').get()
        compare_at_usd = None
        if compare_at_text:
            m_comp = re.search(r'[\$£€]?\s*(\d+(?:\.\d+)?)', compare_at_text)
            if m_comp:
                compare_at_usd = float(m_comp.group(1))

        # Scene7 images
        raw_images = []
        has_variants = product_group.get("hasVariant", []) if product_group else []
        for v in has_variants:
            v_imgs = v.get("image", [])
            if isinstance(v_imgs, (str, dict)):
                v_imgs = [v_imgs]
            for im in v_imgs:
                u = im.get("url") if isinstance(im, dict) else im
                if u and isinstance(u, str):
                    raw_images.append(u)

        raw_data = {
            "title": title,
            "url": url,
            "sku": sku,
            "price": source_price,
            "compare_at_price": compare_at_usd,
            "description": (product_obj.get("description") or "") if product_obj else "",
            "material": (product_obj.get("material") or "") if product_obj else "",
            "images": raw_images,
            "hasVariant": has_variants,
            "bullets": bullets
        }

        canonical = parse_product_payload(raw_data, usd_to_inr_rate=forex_rate, group_name="handbags")
        elapsed_ms = (time.perf_counter() - t0) * 1000
        canonical["_elapsed_ms"] = elapsed_ms
        return canonical

    except Exception as exc:
        print(f"[ERROR] Exception processing {url}: {exc}")
        return None


def run_katespade_ingestion(max_workers: int = 5):
    """Run full multithreaded ingestion for all 429 Kate Spade products."""
    if not os.path.exists(DISCOVERED_URLS_PATH):
        raise FileNotFoundError(f"Missing {DISCOVERED_URLS_PATH}. Run discovery first.")

    with open(DISCOVERED_URLS_PATH, "r", encoding="utf-8") as f:
        urls = json.load(f)

    total_urls = len(urls)
    forex_rate = get_usd_to_inr_rate()
    print("=" * 72)
    print("KATE SPADE OUTLET CATALOG INGESTION")
    print(f"Total Target Products: {total_urls}")
    print(f"Forex Rate:            1 USD = ₹{forex_rate:.2f}")
    print(f"Worker Concurrency:    {max_workers}")
    print("=" * 72)

    saved_count = 0
    errors = 0
    by_category = {}
    total_variants = 0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(fetch_and_parse_pdp, url, forex_rate, 0.15): (idx, url)
            for idx, url in enumerate(urls, start=1)
        }

        for future in as_completed(future_to_url):
            idx, url = future_to_url[future]
            try:
                canonical = future.result()
                if canonical:
                    saved = save_product(canonical, base_dir="storage/db")
                    saved_count += 1
                    v_count = len(saved.get("variants", []))
                    total_variants += v_count
                    cat = saved.get("product_type", "Handbags")
                    by_category[cat] = by_category.get(cat, 0) + 1
                    
                    if saved_count % 10 == 0 or saved_count == total_urls:
                        print(f"[{saved_count:>3}/{total_urls}] {saved['title'][:40]:<40} | ₹{saved['current_price']:>6} | {v_count} vars | {canonical.get('_elapsed_ms', 0):.0f}ms")
                else:
                    errors += 1
            except Exception as err:
                errors += 1
                print(f"[ERROR] Failed SKU {url}: {err}")

    # Rebuild index
    print("\nRebuilding master index.json...")
    master_index = build_and_save_index("storage/db")
    total_master = len(master_index)

    elapsed = time.time() - start_time
    print("\n" + "=" * 72)
    print("KATE SPADE INGESTION COMPLETE")
    print("=" * 72)
    print(f"Successfully Ingested: {saved_count}/{total_urls} products")
    print(f"Total Variants Stored: {total_variants}")
    print(f"Failed / Errors:       {errors}")
    print(f"Master Catalog Total:  {total_master} products across all stores")
    print(f"Ingestion Duration:    {elapsed:.1f} seconds (avg {elapsed/max(1, saved_count):.2f}s/product)")
    print("\nBreakdown by Product Type:")
    for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
        print(f"  - {cat:<24}: {count}")
    print("=" * 72)


if __name__ == "__main__":
    run_katespade_ingestion(max_workers=5)
