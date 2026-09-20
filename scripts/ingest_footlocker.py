"""
Foot Locker Multi-Collection Ingestion Pipeline
Scrapes and ingests footwear from Foot Locker across 5 target collections:
1) Nike Vomero
2) Nike P-6000
3) Nike Mind / Calm
4) adidas Handball Spezial
5) ASICS Shoes

Enforces zero 1-size truncation invariant, separates widths from numeric sizes,
formats whole-rupee INR prices, dynamic brand detection, and persists atomically to storage/db/footlocker/products/.
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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from storage.forex import get_usd_to_inr_rate
from storage.validator import validate_product
from storage.db import save_product, build_and_save_index
from stores.footlocker.inflow import parse_product_payload

CACHE_DIR = "scratch/fl_raw_pdp"
HARVESTED_FILE = "scratch/harvested_full.json"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

TARGET_COLLECTIONS = [
    {
        "name": "Nike Vomero",
        "group": "Nike Vomero",
        "query": "nike+vomero%3Arelevance%3Agender%3AMen%27s%3Agender%3AWomen%27s%3AproductType%3AShoes"
    },
    {
        "name": "Nike P-6000",
        "group": "Nike P-6000",
        "query": "nike+p+6000%3Arelevance%3Agender%3AMen%27s%3Agender%3AWomen%27s"
    },
    {
        "name": "Nike Mind",
        "group": "Nike Mind",
        "query": "Nike%20mind"
    },
    {
        "name": "adidas Handball Spezial",
        "group": "adidas Handball Spezial",
        "query": "handball%20spezial%3Arelevance%3Agender%3AMen%27s%3Agender%3AWomen%27s"
    },
    {
        "name": "ASICS Shoes",
        "group": "ASICS Shoes",
        "query": "asics+shoes%3Arelevance%3Agender%3AMen%27s%3Agender%3AWomen%27s"
    }
]


COLORS_TO_SLICE = [
    "White", "Black", "Grey", "Pink", "Blue", "Tan", "Green", "Red", "Brown", "Silver", "Orange", "Purple", "Gold", "Yellow", "Beige", "Multi"
]


def harvest_target(target: Dict[str, str], client: httpx.Client) -> List[Dict[str, Any]]:
    """Harvest all products from a search target using multi-dimensional sort & color slicing."""
    discovered = {}
    q_base = target["query"]
    group = target["group"]
    name = target["name"]

    print(f"\n--- Harvesting Target: {name} ---")

    # 1. Base query
    url = f"https://www.footlocker.com/search?query={q_base}"
    try:
        r = client.get(url, headers=HEADERS, follow_redirects=True, timeout=20.0)
        if r.status_code == 200:
            idx = r.text.find('STATE_FROM_SERVER:')
            if idx != -1:
                d, _ = json.JSONDecoder().raw_decode(r.text[idx + len('STATE_FROM_SERVER:'):].lstrip())
                for p in d.get('search', {}).get('products', []):
                    sku = p.get('sku')
                    if sku:
                        discovered[sku] = {
                            "sku": sku,
                            "name": p.get('name') or name,
                            "group": group
                        }
    except Exception as e:
        print(f"  [WARN] Base query error on {name}: {e}")

    # 2. Sort slices
    for sort_name in ["price-ascending", "price-descending", "newArrivals"]:
        q_sort = q_base.replace("%3Arelevance", f"%3A{sort_name}").replace(":relevance", f":{sort_name}")
        url = f"https://www.footlocker.com/search?query={q_sort}"
        try:
            r = client.get(url, headers=HEADERS, follow_redirects=True, timeout=20.0)
            if r.status_code == 200:
                idx = r.text.find('STATE_FROM_SERVER:')
                if idx != -1:
                    d, _ = json.JSONDecoder().raw_decode(r.text[idx + len('STATE_FROM_SERVER:'):].lstrip())
                    for p in d.get('search', {}).get('products', []):
                        sku = p.get('sku')
                        if sku and sku not in discovered:
                            discovered[sku] = {
                                "sku": sku,
                                "name": p.get('name') or name,
                                "group": group
                            }
        except Exception:
            pass

    # 3. Primary Color slices
    for c in COLORS_TO_SLICE:
        q_color = f"{q_base}%3AprimaryColor%3A{c}"
        url = f"https://www.footlocker.com/search?query={q_color}"
        try:
            r = client.get(url, headers=HEADERS, follow_redirects=True, timeout=20.0)
            if r.status_code == 200:
                idx = r.text.find('STATE_FROM_SERVER:')
                if idx != -1:
                    d, _ = json.JSONDecoder().raw_decode(r.text[idx + len('STATE_FROM_SERVER:'):].lstrip())
                    for p in d.get('search', {}).get('products', []):
                        sku = p.get('sku')
                        if sku and sku not in discovered:
                            discovered[sku] = {
                                "sku": sku,
                                "name": p.get('name') or name,
                                "group": group
                            }
        except Exception:
            pass

    print(f"  Total discovered for {name}: {len(discovered)} products")
    return list(discovered.values())


def harvest_all_collections() -> List[Dict[str, Any]]:
    """Harvest across all 5 target collections and save combined discovered inventory."""
    all_discovered = {}
    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=25.0) as client:
        for target in TARGET_COLLECTIONS:
            target_prods = harvest_target(target, client)
            for p in target_prods:
                sku = p["sku"]
                if sku not in all_discovered:
                    all_discovered[sku] = p

    os.makedirs(os.path.dirname(HARVESTED_FILE), exist_ok=True)
    with open(HARVESTED_FILE, "w", encoding="utf-8") as f:
        json.dump(list(all_discovered.values()), f, indent=2)

    print(f"\n[HARVEST COMPLETE] Total unique products discovered across all 5 targets: {len(all_discovered)}")
    return list(all_discovered.values())


def fetch_and_extract_pdp(sku: str, title: str, group: str, client: httpx.Client) -> Optional[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
    """
    Fetch PDP HTML and extract hydrated data and high-res images.
    Also extracts sibling colorways from styleVariants (Anti-Omission Standard).
    Caches raw extraction to disk.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, f"{sku}.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
                return cached_data, []
        except Exception:
            pass

    pdp_url = f"https://www.footlocker.com/product/~/{sku}.html"

    for attempt in range(3):
        try:
            r = client.get(pdp_url, headers=HEADERS, follow_redirects=True, timeout=25.0)
            if r.status_code == 404:
                return None
            if r.status_code != 200:
                time.sleep(1.0)
                continue

            html = r.text
            idx = html.find('STATE_FROM_SERVER:')
            if idx == -1:
                return None

            d, _ = json.JSONDecoder().raw_decode(html[idx + len('STATE_FROM_SERVER:'):].lstrip())
            data = d.get('api', {}).get('productDetails', {}).get('getDetails', {}).get('data', {})
            if not data:
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
            data['pdp_url'] = str(r.url) if r.url else pdp_url

            # Discover sibling styleVariants (Anti-Omission Standard)
            sibling_items = []
            for sv in data.get('styleVariants', []):
                s_sku = sv.get('sku')
                if s_sku and s_sku != sku:
                    sibling_items.append({
                        "sku": s_sku,
                        "name": title,
                        "group": group
                    })

            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f)

            return data, sibling_items
        except Exception as e:
            if attempt == 2:
                return None
            time.sleep(1.0)
    return None


def run_footlocker_ingestion(max_workers: int = 6) -> int:
    print("=" * 72)
    print("FOOT LOCKER MULTI-COLLECTION INGESTION PIPELINE")
    print("=" * 72)

    # 1. Harvest across all 5 target search collections
    discovered = harvest_all_collections()
    forex_rate = get_usd_to_inr_rate()
    print(f"Live USD -> INR Forex Rate: ₹{forex_rate:.2f}")

    products_to_fetch = {item['sku']: (item.get('name') or "Shoes", item.get('group') or "Foot Locker") for item in discovered if item.get('sku')}

    print(f"\nFetching and parsing {len(products_to_fetch)} product detail pages with {max_workers} workers...")

    success_count = 0
    truncated_count = 0
    skipped_count = 0
    in_stock_count = 0
    out_of_stock_count = 0

    fetched_skus = set()

    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=25.0) as client:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Round 1: Fetch all discovered search products
            pending_futures = {
                executor.submit(fetch_and_extract_pdp, sku, name, group, client): (sku, name, group)
                for sku, (name, group) in products_to_fetch.items()
            }

            while pending_futures:
                for future in list(as_completed(pending_futures)):
                    sku, name, group = pending_futures.pop(future)
                    fetched_skus.add(sku)
                    try:
                        res = future.result()
                        if not res:
                            skipped_count += 1
                            continue

                        raw_data, sibling_items = res
                        canonical = parse_product_payload(raw_data, forex_rate=forex_rate, group_name=group)
                        if not canonical:
                            skipped_count += 1
                            continue

                        variants = canonical.get("variants", [])
                        if len(variants) <= 1:
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

                        print(f"  [SAVED] {sku:10s} | {canonical['vendor']:8s} | {canonical['title'][:32]:32s} | {len(variants):2d} sizes | ₹{canonical['current_price']:.0f} | {canonical['availability']}")

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
    print(f"Skipped / Non-Adult/Err  : {skipped_count}")
    print("=" * 72)

    return success_count


if __name__ == "__main__":
    run_footlocker_ingestion()

