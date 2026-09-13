"""
Coach Catalog Inflow Orchestrator
Fetches all discovered Coach PDPs, extracts canonical attributes, builds accordion size guides,
and persists canonical records atomically to storage/db/coach/products/{product_id}.json.
Pure functional composition, zero classes (ADR 0004, ADR 0005, ADR 0006).
"""
import os
import sys
import json
import time
import re
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional
import httpx

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.getcwd())

from storage.network import get_browser_headers, create_http_client
from storage.forex import get_usd_to_inr_rate
from storage.rate_limiter import acquire_permit
from storage.db import generate_product_id
import stores.coach.inflow as coach_inflow

OUTPUT_DIR = "storage/db/coach/products"
MANIFEST_PATH = "scratch/robust_crawl_summary.json"


def clean_html_tags(text: str) -> str:
    """Remove HTML tags, script, and style blocks."""
    cleaned = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<script[^>]*>.*?</script>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def parse_pdp_html(html_text: str, url: str, group_name: str, gender: str) -> Dict[str, Any]:
    """Extract raw product attributes from Coach PDP HTML."""
    # 1. Parse JSON-LD
    json_lds = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html_text, re.DOTALL)
    product_group = {}
    product_single = {}
    for block in json_lds:
        try:
            d = json.loads(block)
            t = d.get("@type")
            if t == "ProductGroup":
                product_group = d
            elif t == "Product":
                product_single = d
        except Exception:
            pass

    # Title
    title = (product_group or product_single or {}).get("name", "")
    if not title:
        m_title = re.search(r'<title>(.*?)</title>', html_text)
        if m_title:
            title = m_title.group(1).split("|")[0].strip()

    # Style Code from URL: /products/.../CR899.html or CR899-BLK.html
    m_style = re.search(r'/([A-Za-z0-9]+)(?:-[^/]+)?\.html', url)
    style_code = m_style.group(1).upper() if m_style else ""

    # Base SKU
    sku = (product_single or {}).get("sku") or style_code or f"COACH-{title[:8].upper()}"

    # Price
    offers = (product_single or {}).get("offers", {})
    if isinstance(offers, list) and offers:
        offers = offers[0]
    price = offers.get("price") or offers.get("lowPrice")
    if not price:
        m_price = re.search(r'"price":\s*([0-9.]+)', html_text)
        if m_price:
            price = float(m_price.group(1))
    price = float(price or 0.0)

    # Description & Bullet points
    desc = (product_single or {}).get("description", "")
    
    # Strip style/script tags first before extracting bullets
    clean_html_for_bullets = re.sub(r'<style[^>]*>.*?</style>', '', html_text, flags=re.DOTALL | re.IGNORECASE)
    clean_html_for_bullets = re.sub(r'<script[^>]*>.*?</script>', '', clean_html_for_bullets, flags=re.DOTALL | re.IGNORECASE)
    
    raw_bullets = re.findall(r'<li[^>]*>(.*?)</li>', clean_html_for_bullets)
    clean_bullets = []
    for b in raw_bullets:
        cb = clean_html_tags(b)
        if not cb or "{" in cb or "}" in cb or "var(--" in cb:
            continue
        if any(k in cb.lower() for k in [
            'leather', 'drop', 'strap', 'pocket', 'style no', 'l) x', 'w)',
            'canvas', 'zip', 'compartment', 'heel', 'sole', 'suede', 'lining',
            'closure', 'credit card', 'dimensions', 'width', 'height'
        ]):
            clean_bullets.append(cb)

    # Scene7 Images - Scoped strictly to this product's style code
    style_prefix = style_code.lower()
    scene7_matches = set(re.findall(r'https://coach\.scene7\.com/is/image/Coach/([a-zA-Z0-9_\-]+)', html_text))
    
    prod_images = []
    # Primary: images starting with the style code
    for img_name in sorted(scene7_matches):
        if img_name.lower().startswith(f"{style_prefix}_"):
            full_img = f"https://coach.scene7.com/is/image/Coach/{img_name}"
            if full_img not in prod_images:
                prod_images.append(full_img)

    # Fallback to JSON-LD images if none matched prefix
    if not prod_images:
        json_imgs = (product_single or {}).get("image", [])
        if isinstance(json_imgs, str):
            json_imgs = [json_imgs]
        for ji in json_imgs:
            clean_ji = ji.split("?")[0].strip()
            if clean_ji and clean_ji not in prod_images:
                prod_images.append(clean_ji)

    # Shoe size buttons
    shoe_sizes = []
    size_buttons = re.findall(r'<button[^>]*class="[^"]*variation-size[^"]*"[^>]*data-qa="([^"]+)"[^>]*>([^<]+)</button>', html_text)
    for qa, sz in size_buttons:
        shoe_sizes.append({
            "size": sz.strip(),
            "in_stock": "enbld" in qa.lower()
        })

    # Color from JSON-LD
    color_val = (product_single or {}).get("color", "")

    return {
        "title": title,
        "sku": sku,
        "style_code": style_code,
        "url": url,
        "price": price,
        "description": desc,
        "bullets": clean_bullets,
        "images": prod_images,
        "shoe_sizes": shoe_sizes,
        "color": color_val,
        "gender": gender,
        "group": group_name
    }


def fetch_and_process_product(
    item: Dict[str, Any],
    client: httpx.Client,
    forex_rate: float,
    headers: Dict[str, str]
) -> Dict[str, Any]:
    """Fetch PDP and transform into canonical record."""
    url = item["url"]
    if url.startswith("/"):
        url = f"https://www.coach.com{url}"
    group_name = item.get("group", "bags")
    gender = item.get("gender", "Women")

    acquire_permit("coach", requests_per_second=2.0, delay_seconds=0.5)

    resp = client.get(url)
    resp.raise_for_status()

    raw_data = parse_pdp_html(resp.text, url, group_name, gender)
    canonical = coach_inflow.parse_product_payload(raw_data, forex_rate, group_name)

    # Deduplication Primary Key: deterministic SHA256("coach::" + sku.lower())[:16]
    clean_sku = canonical["source_sku"].strip()
    product_id = generate_product_id("coach", clean_sku)
    canonical["id"] = product_id
    canonical["product_id"] = product_id
    canonical["store"] = "coach"

    # Save atomically to disk: .tmp + os.replace
    out_file = os.path.join(OUTPUT_DIR, f"{product_id}.json")
    tmp_file = f"{out_file}.tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(canonical, f, indent=2, ensure_ascii=False)
    os.replace(tmp_file, out_file)

    return {
        "product_id": product_id,
        "sku": clean_sku,
        "title": canonical["title"],
        "price_usd": canonical["source_price"],
        "price_inr": canonical["current_price"],
        "variants_count": len(canonical["variants"]),
        "images_count": len(canonical["images"]),
        "has_accordion": "size-guide-accordion" in canonical["descriptionHtml"]
    }


def run_coach_inflow(max_workers: int = 3) -> None:
    """Execute complete catalog ingestion pipeline for Coach."""
    start_time = time.time()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        summary = json.load(f)

    # Collect all unique URLs with their metadata
    unique_items: Dict[str, Dict[str, Any]] = {}
    for cat_name, cat_data in summary.items():
        gender = "Women" if "women" in cat_name.lower() else "Men"
        if "wallet" in cat_name.lower():
            grp = "men_wallets" if gender == "Men" else "women_wallets"
        elif "shoe" in cat_name.lower():
            grp = "men_shoes" if gender == "Men" else "women_shoes"
        elif "wristlet" in cat_name.lower():
            grp = "women_wristlets"
        else:
            grp = "men_bags" if gender == "Men" else "women_bags"

        for u in cat_data.get("urls", []):
            if u not in unique_items:
                unique_items[u] = {
                    "url": u,
                    "group": grp,
                    "gender": gender,
                    "category": cat_name
                }

    items_list = list(unique_items.values())
    total_items = len(items_list)
    print(f"[*] Starting Coach Inflow Pipeline for {total_items} unique products...")
    print(f"[*] Target Directory: {OUTPUT_DIR}")

    forex_rate = get_usd_to_inr_rate()
    print(f"[*] Live USD->INR Forex Rate: {forex_rate:.4f}")

    headers = get_browser_headers({"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})

    success_count = 0
    error_count = 0
    total_variants = 0

    with create_http_client(custom_headers=headers, timeout_seconds=20.0) as client:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {
                executor.submit(fetch_and_process_product, item, client, forex_rate, headers): item["url"]
                for item in items_list
            }

            for idx, future in enumerate(as_completed(future_to_url), 1):
                url = future_to_url[future]
                try:
                    res = future.result()
                    success_count += 1
                    total_variants += res["variants_count"]
                    if idx % 25 == 0 or idx == total_items:
                        pct = round((idx / total_items) * 100, 1)
                        print(f"[{idx}/{total_items} ({pct}%)] [OK] {res['sku']} | {res['title'][:30]} | ${res['price_usd']} -> ₹{res['price_inr']} | Vars: {res['variants_count']} | Imgs: {res['images_count']}")
                except Exception as e:
                    error_count += 1
                    print(f"[{idx}/{total_items}] [ERROR] {url}: {e}")

    elapsed = round(time.time() - start_time, 2)
    print(f"\n========================================================")
    print(f"[✓] Coach Ingestion Finished in {elapsed}s!")
    print(f"    Total Products Processed: {total_items}")
    print(f"    Successfully Ingested:   {success_count}")
    print(f"    Errors:                   {error_count}")
    print(f"    Total Variants Created:   {total_variants}")
    print(f"========================================================")


if __name__ == "__main__":
    run_coach_inflow()
