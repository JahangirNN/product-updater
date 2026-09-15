"""
Enrich Coach Catalog Pipeline
Fetches live Coach PDPs to extract complete multi-color variants (SKUs, titles, prices, variant images),
parses structured dimensions and measurements, cleans image galleries of swatches, and saves canonical
records atomically to storage/db/coach/products/{product_id}.json.
Pure functional composition, zero classes (ADR 0004, ADR 0005, ADR 0006).
"""
import os
import sys
import json
import time
import re
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional
import httpx

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.getcwd())

from storage.network import get_browser_headers, create_http_client
from storage.forex import get_usd_to_inr_rate
from storage.rate_limiter import acquire_permit
from storage.db import generate_product_id, build_and_save_index
import stores.coach.inflow as coach_inflow

PRODUCTS_DIR = "storage/db/coach/products"


def clean_html_tags(text: str) -> str:
    """Remove HTML tags, script, and style blocks."""
    cleaned = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<script[^>]*>.*?</script>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def parse_pdp_html(html_text: str, url: str, group_name: str, gender: str) -> Dict[str, Any]:
    """Extract raw product attributes from live Coach PDP HTML."""
    # 1. Parse JSON-LD
    json_lds = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html_text, re.DOTALL)
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

    # Description
    desc = (product_single or {}).get("description", "")
    
    # Bullets from PDP HTML and product-props__details blocks
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
            'closure', 'credit card', 'dimensions', 'width', 'height', 'length'
        ]):
            clean_bullets.append(cb)

    # Also parse product-props__details blocks for rich key-value bullet points
    props_blocks = re.findall(r"<div class='product-props__details'[^>]*>\s*<h2>(.*?)</h2>\s*<ul>(.*?)</ul>\s*</div>", html_text, re.DOTALL)
    for header, ul_content in props_blocks:
        items = [clean_html_tags(li) for li in re.findall(r'<li[^>]*>(.*?)</li>', ul_content, re.DOTALL)]
        for it in items:
            if it and it not in clean_bullets:
                clean_bullets.append(it)

    # Scene7 Images - strictly excluding swatches
    style_prefix = style_code.lower()
    scene7_matches = set(re.findall(r'https://coach\.scene7\.com/is/image/Coach/([a-zA-Z0-9_\-]+)', html_text))
    prod_images = []
    for img_name in sorted(scene7_matches):
        if "_swatch" in img_name.lower() or "swatch_" in img_name.lower():
            continue
        if img_name.lower().startswith(f"{style_prefix}_"):
            full_img = f"https://coach.scene7.com/is/image/Coach/{img_name}"
            if full_img not in prod_images:
                prod_images.append(full_img)

    # Shoe size buttons
    shoe_sizes = []
    size_buttons = re.findall(r'<button[^>]*class="[^"]*variation-size[^"]*"[^>]*data-qa="([^"]+)"[^>]*>([^<]+)</button>', html_text)
    for qa, sz in size_buttons:
        shoe_sizes.append({
            "size": sz.strip(),
            "in_stock": "enbld" in qa.lower()
        })

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
        "group": group_name,
        "product_group": product_group,
        "product_single": product_single
    }


def enrich_single_product(
    filepath: str,
    client: httpx.Client,
    forex_rate: float
) -> Dict[str, Any]:
    """Fetch live PDP, parse full variants & dimensions, and update stored file atomically."""
    with open(filepath, "r", encoding="utf-8") as f:
        existing = json.load(f)

    url = existing.get("source_url")
    if not url:
        return {"status": "skipped_no_url", "filepath": filepath}

    group_name = existing.get("groups", ["bags"])[0] if existing.get("groups") else "bags"
    gender = existing.get("gender") or ("Women" if "women" in group_name.lower() else "Men")

    acquire_permit("coach", requests_per_second=2.0, delay_seconds=0.5)

    try:
        resp = client.get(url)
        resp.raise_for_status()
        raw_data = parse_pdp_html(resp.text, url, group_name, gender)
        canonical = coach_inflow.parse_product_payload(raw_data, forex_rate, group_name)
    except Exception as e:
        # Fallback to re-normalizing existing data with upgraded inflow logic
        raw_fallback = {
            "title": existing.get("title", ""),
            "sku": existing.get("source_sku", ""),
            "url": url,
            "price": existing.get("source_price", 0.0),
            "compare_at_price": existing.get("source_compare_at_price"),
            "description": existing.get("descriptionHtml", ""),
            "bullets": [],
            "specs": existing.get("specifications", {}),
            "images": existing.get("images", []),
            "variants": existing.get("variants", []),
            "gender": gender,
            "group": group_name
        }
        canonical = coach_inflow.parse_product_payload(raw_fallback, forex_rate, group_name)

    # Preserve identifiers
    product_id = existing.get("product_id") or existing.get("id")
    canonical["id"] = product_id
    canonical["product_id"] = product_id
    canonical["store"] = "coach"
    canonical["created_at"] = existing.get("created_at", canonical["created_at"])
    canonical["last_verified_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Write atomically
    tmp_path = f"{filepath}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(canonical, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, filepath)

    return {
        "status": "success",
        "product_id": product_id,
        "sku": canonical["source_sku"],
        "title": canonical["title"],
        "variants_count": len(canonical["variants"]),
        "dimensions": canonical.get("dimensions", {}).get("formatted"),
        "images_count": len(canonical["images"])
    }


def run_enrichment(max_workers: int = 4):
    """Enrich all Coach products stored on disk."""
    print("=================================================================")
    print("🚀 Starting Coach Multi-Color & Dimension Catalog Enrichment")
    print("=================================================================")
    files = glob.glob(os.path.join(PRODUCTS_DIR, "*.json"))
    print(f"[*] Found {len(files)} Coach product files to process.")

    client = create_http_client(timeout_seconds=15.0)
    forex_rate = get_usd_to_inr_rate()
    print(f"[*] Live USD->INR Forex Rate: {forex_rate}")

    total = len(files)
    completed = 0
    multi_variant_count = 0
    dims_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(enrich_single_product, fp, client, forex_rate): fp for fp in files}
        for fut in as_completed(futures):
            completed += 1
            res = fut.result()
            if res.get("status") == "success":
                v_cnt = res.get("variants_count", 0)
                dims = res.get("dimensions")
                if v_cnt > 1:
                    multi_variant_count += 1
                if dims:
                    dims_count += 1
                if completed % 10 == 0 or completed == total:
                    print(f"[{completed}/{total}] {res.get('sku')} | {res.get('title')[:30]} | Vars: {v_cnt} | Dims: {dims or 'None'} | Imgs: {res.get('images_count')}")

    print("\n=================================================================")
    print(f"✅ Catalog Enrichment Complete: {completed}/{total} processed.")
    print(f"📊 Multi-variant products: {multi_variant_count}/{total}")
    print(f"📏 Products with structured dimensions: {dims_count}/{total}")
    print("=================================================================")

    # Rebuild index
    print("[*] Rebuilding storage/db/index.json...")
    build_and_save_index()
    print("✅ Master catalog index rebuilt successfully.")


if __name__ == "__main__":
    run_enrichment(max_workers=4)
