"""
JW PEI Search Catalog Ingestion Pipeline
Ingests products from JW PEI search query (Noor, Carmen, Hana) into the partitioned JSON database.
Strictly filters for bags only and rejects clothing/apparel.
Uses dual-endpoint extraction (/products/{handle}.json and /products/{handle}.js) for full fidelity.
Pure functions, zero classes (ADR 0004, ADR 0005, ADR 0006).
"""
import os
import sys
import json
import time
import re
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Tuple, Optional, Set
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from storage.forex import get_usd_to_inr_rate
from storage.validator import validate_product
from storage.db import save_product, build_and_save_index, generate_product_id
from stores.jwpei.inflow import parse_product_payload

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

BAG_KEYWORDS = [
    "bag", "tote", "clutch", "crossbody", "shoulder", "wallet",
    "satchel", "hobo", "bucket", "pouch", "backpack", "top-handle", "top handle"
]

CLOTHING_KEYWORDS = [
    "dress", "skirt", "coat", "jacket", "pant", "shirt",
    "blazer", "sweater", "cardigan", "apparel", "clothing", "gown"
]


def is_bag_product(handle: str, title: str = "", product_type: str = "") -> bool:
    """
    Strict filter: strictly ingest bags only.
    Rejects any dresses, skirts, coats, jackets, clothing/apparel.
    """
    text_to_check = f"{handle} {title} {product_type}".lower()

    # Reject if matches clothing keywords (word boundary or token match)
    for c_kw in CLOTHING_KEYWORDS:
        pattern = rf"(?:\b|_|-){re.escape(c_kw)}(?:\b|_|-|s\b)"
        if re.search(pattern, text_to_check) or c_kw in product_type.lower():
            return False

    # Must contain at least one bag keyword
    has_bag_kw = any(b_kw in text_to_check for b_kw in BAG_KEYWORDS)
    return has_bag_kw



def discover_search_handles(
    query: str = "Noor carmen hana",
    max_pages: int = 6,
    client: Optional[httpx.Client] = None
) -> List[str]:
    """
    Discover product handles from JW PEI search pages 1 to max_pages.
    """
    base_url = "https://www.jwpei.com/search?options%5Bprefix%5D=last&page={page}&q={query}&type=product"
    handles = []
    seen = set()

    should_close = False
    if client is None:
        client = httpx.Client(headers=HEADERS, timeout=15.0)
        should_close = True

    try:
        for page in range(1, max_pages + 1):
            url = base_url.format(page=page, query=query.replace(" ", "+"))
            try:
                resp = client.get(url)
                if resp.status_code != 200:
                    print(f"[WARN] Search page {page} returned status {resp.status_code}. Stopping discovery.")
                    break

                page_handles = re.findall(r'href=[\"\']/products/([a-zA-Z0-9\-_]+)[\"\']', resp.text)
                new_page_count = 0
                for h in page_handles:
                    if h not in seen and not h.endswith(('.js', '.json', '.css', '.png', '.jpg')):
                        seen.add(h)
                        handles.append(h)
                        new_page_count += 1

                print(f"  Discovery Page {page}: found {new_page_count} handles (total unique so far: {len(handles)})")
                if new_page_count == 0:
                    break
                time.sleep(0.15)
            except Exception as e:
                print(f"[ERROR] Error fetching search page {page}: {e}")
    finally:
        if should_close:
            client.close()

    return handles


def fetch_dual_endpoint_with_backoff(
    handle: str,
    client: httpx.Client,
    max_retries: int = 5
) -> Tuple[str, Dict[str, Any], Optional[str]]:
    """
    Dual-endpoint extraction:
    - /products/{handle}.js for live availability, price cents, variant details
    - /products/{handle}.json for full attributes, images, size guides, description
    Returns (handle, merged_raw_data, error_message).
    """
    url_js = f"https://www.jwpei.com/products/{handle}.js"
    url_json = f"https://www.jwpei.com/products/{handle}.json"

    data_js = None
    for attempt in range(max_retries):
        try:
            resp_js = client.get(url_js, timeout=14.0)
            if resp_js.status_code == 429:
                time.sleep(2.0 * (attempt + 1))
                continue
            if resp_js.status_code == 404:
                return handle, {}, "HTTP 404 (Delisted/Not Found on .js)"
            resp_js.raise_for_status()
            data_js = resp_js.json()
            break
        except Exception as err:
            if attempt == max_retries - 1:
                return handle, {}, f".js error: {err}"
            time.sleep(1.5 * (attempt + 1))

    if data_js is None:
        return handle, {}, "Rate limited on .js"

    time.sleep(0.12)

    data_json = {}
    for attempt in range(max_retries):
        try:
            resp_json = client.get(url_json, timeout=14.0)
            if resp_json.status_code == 429:
                time.sleep(2.0 * (attempt + 1))
                continue
            if resp_json.status_code == 404:
                # Fallback to .js alone if .json is 404
                data_json = {}
                break
            resp_json.raise_for_status()
            data_json = resp_json.json().get("product", {})
            break
        except Exception as err:
            if attempt == max_retries - 1:
                # If json fails, we can fall back to js
                data_json = {}
                break
            time.sleep(1.5 * (attempt + 1))

    # Merge: .json has full rich body_html and images; .js has live available & price
    merged = dict(data_json) if data_json else dict(data_js)
    merged["available"] = data_js.get("available")
    if data_js.get("price") is not None:
        merged["price"] = data_js.get("price") / 100.0
    if data_js.get("compare_at_price") is not None:
        merged["compare_at_price"] = data_js.get("compare_at_price") / 100.0

    # Ensure body_html is present
    if not merged.get("body_html") and data_js.get("description"):
        merged["body_html"] = data_js.get("description")

    # Merge images if needed
    if not merged.get("images") and data_js.get("images"):
        merged["images"] = data_js.get("images")

    # Merge variants availability
    if merged.get("variants") and data_js.get("variants"):
        merged["variants"][0]["available"] = data_js.get("available")
        if "sku" not in merged["variants"][0] or not merged["variants"][0]["sku"]:
            merged["variants"][0]["sku"] = data_js["variants"][0].get("sku")

    time.sleep(0.12)  # Polite pacing delay
    return handle, merged, None


def process_and_save_product(
    handle: str,
    raw_data: Dict[str, Any],
    forex_rate: float
) -> Optional[Dict[str, Any]]:
    """
    Parse canonical product record, validate, and save to partitioned database.
    Returns summary dict or None if filtered out.
    """
    # Guard against non-bag items
    title = raw_data.get("title", "")
    p_type = raw_data.get("product_type") or raw_data.get("type") or ""
    if not is_bag_product(handle, title, p_type):
        print(f"[FILTERED] Skipping non-bag item: {handle} ({title})")
        return None

    canonical = parse_product_payload(raw_data, usd_to_inr_rate=forex_rate, group_name="handbags")

    # Enforce primary key requirement: SHA256("jwpei::" + sku)[:16]
    sku = canonical.get("source_sku", "")
    product_id = generate_product_id("jwpei", sku)
    canonical["id"] = product_id

    # Validation
    is_valid, status, warnings = validate_product(canonical)
    canonical["status"] = status
    canonical["validation_warnings"] = warnings

    # Atomic write to storage/db/jwpei/products/{product_id}.json
    saved = save_product(canonical)

    return {
        "handle": handle,
        "id": saved["id"],
        "title": saved["title"],
        "sku": saved["source_sku"],
        "price_usd": saved["source_price"],
        "price_inr": saved["current_price"],
        "availability": saved["availability"],
        "status": status,
        "images_count": len(saved["images"]),
        "has_specs": len(saved["specifications"]) > 0,
        "material": saved.get("material")
    }


def run_search_inflow(
    handles_file: Optional[str] = "scratch/search_handles.json",
    max_workers: int = 3,
    force_rediscover: bool = False
) -> Dict[str, Any]:
    """
    Run end-to-end ingestion pipeline for search handles.
    """
    print("=" * 72)
    print("JW PEI SEARCH CATALOG INGESTION (NOOR, CARMEN & HANA)")
    print("=" * 72)

    # 1. Obtain handles
    handles: List[str] = []
    if not force_rediscover and handles_file and os.path.exists(handles_file):
        print(f"Loading search handles from cache: {handles_file}")
        with open(handles_file, "r", encoding="utf-8") as f:
            handles = json.load(f)
        print(f"Loaded {len(handles)} handles from cache.")
    else:
        print("Discovering search handles live across Pages 1 to 6...")
        handles = discover_search_handles()
        print(f"Discovered {len(handles)} unique handles.")
        if handles_file:
            os.makedirs(os.path.dirname(handles_file), exist_ok=True)
            with open(handles_file, "w", encoding="utf-8") as f:
                json.dump(handles, f, indent=2)

    # Apply strict bag pre-filter on handles
    bag_handles = [h for h in handles if is_bag_product(h)]
    rejected_count = len(handles) - len(bag_handles)
    if rejected_count > 0:
        print(f"[GUARD] Pre-filtered {rejected_count} non-bag handles. {len(bag_handles)} bag handles remain.")
    else:
        print(f"All {len(bag_handles)} handles passed bag taxonomy filter.")

    total = len(bag_handles)

    # 2. Get live exchange rate
    forex_rate = get_usd_to_inr_rate()
    print(f"USD -> INR Exchange Rate: ₹{forex_rate:.4f} (Cached 24h)")

    # Check which handles are already ingested and valid on disk
    existing_handles_map: Dict[str, Dict[str, Any]] = {}
    products_dir = "storage/db/jwpei/products"
    if os.path.exists(products_dir):
        for f in os.listdir(products_dir):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(products_dir, f), "r", encoding="utf-8") as fp:
                        d = json.load(fp)
                    h = d.get("handle")
                    if h and len(d.get("images", [])) > 0 and len(d.get("specifications", {})) > 0 and d.get("source_sku"):
                        existing_handles_map[h] = {
                            "handle": h,
                            "id": d.get("id"),
                            "title": d.get("title"),
                            "sku": d.get("source_sku"),
                            "price_usd": d.get("source_price"),
                            "price_inr": d.get("current_price"),
                            "availability": d.get("availability"),
                            "status": d.get("status", "ACTIVE"),
                            "images_count": len(d.get("images", [])),
                            "has_specs": True,
                            "material": d.get("material")
                        }
                except Exception:
                    pass

    already_done = [existing_handles_map[h] for h in bag_handles if h in existing_handles_map]
    handles_to_fetch = [h for h in bag_handles if h not in existing_handles_map]

    print(f"Already verified on disk: {len(already_done)}/{total} items.")
    print(f"Remaining to fetch:       {len(handles_to_fetch)} items.")

    start_time = time.time()
    results: List[Dict[str, Any]] = list(already_done)
    failed: List[Dict[str, str]] = []
    filtered_out: List[str] = []

    if handles_to_fetch:
        print(f"\nStarting polite concurrent ingestion ({max_workers} workers) for {len(handles_to_fetch)} items...")
        with httpx.Client(headers=HEADERS) as client:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_handle = {
                    executor.submit(fetch_dual_endpoint_with_backoff, handle, client): handle
                    for handle in handles_to_fetch
                }

                completed_count = 0
                to_fetch_total = len(handles_to_fetch)
                for future in as_completed(future_to_handle):
                    completed_count += 1
                    handle, raw_data, err = future.result()

                    if err:
                        failed.append({"handle": handle, "error": err})
                        print(f"[{completed_count:3d}/{to_fetch_total}] FAIL: {handle} -> {err}")
                        continue

                    try:
                        summary = process_and_save_product(handle, raw_data, forex_rate)
                        if summary:
                            results.append(summary)
                            print(
                                f"[{completed_count:3d}/{to_fetch_total}] Ingested: {summary['title'][:32]} | "
                                f"₹{summary['price_inr']:,.0f} | {summary['availability']} | "
                                f"{summary['status']} | {summary['images_count']} imgs"
                            )
                        else:
                            filtered_out.append(handle)
                    except Exception as parse_err:
                        failed.append({"handle": handle, "error": str(parse_err)})
                        print(f"[{completed_count:3d}/{to_fetch_total}] PARSE ERROR: {handle} -> {parse_err}")

    # 3. Rebuild global master index
    print("\nUpdating master storage index (storage/db/index.json)...")
    index_map = build_and_save_index()

    total_time = time.time() - start_time
    active_count = sum(1 for r in results if r["status"] == "ACTIVE")
    draft_count = sum(1 for r in results if r["status"] == "DRAFT")
    in_stock_count = sum(1 for r in results if r["availability"] == "in_stock")
    out_stock_count = sum(1 for r in results if r["availability"] == "out_of_stock")

    print("\n" + "=" * 72)
    print("SEARCH INGESTION SUMMARY")
    print("=" * 72)
    print(f"Target Handles Discovered: {total}")
    print(f"Successfully Ingested:     {len(results)}")
    print(f"Filtered (Non-Bags):       {len(filtered_out)}")
    print(f"Failed / Request Errors:   {len(failed)}")
    print(f"Active Products:           {active_count}")
    print(f"Draft Products:            {draft_count}")
    print(f"In Stock:                  {in_stock_count}")
    print(f"Out of Stock:              {out_stock_count}")
    print(f"Master Catalog Total:      {len(index_map)} items in storage/db/index.json")
    print(f"Elapsed Time:              {total_time:.2f} seconds ({total_time/max(total, 1):.2f}s/product)")
    print("=" * 72)

    return {
        "total_targets": total,
        "ingested": len(results),
        "failed": len(failed),
        "filtered": len(filtered_out),
        "catalog_total": len(index_map),
        "results": results
    }


def main():
    parser = argparse.ArgumentParser(description="JW PEI Search Ingestion Pipeline")
    parser.add_argument("--workers", type=int, default=3, help="Max worker threads (default: 3)")
    parser.add_argument("--handles-file", type=str, default="scratch/search_handles.json", help="Path to handles JSON")
    parser.add_argument("--rediscover", action="store_true", help="Force live search re-discovery")

    args = parser.parse_args()
    run_search_inflow(
        handles_file=args.handles_file,
        max_workers=args.workers,
        force_rediscover=args.rediscover
    )


if __name__ == "__main__":
    main()
