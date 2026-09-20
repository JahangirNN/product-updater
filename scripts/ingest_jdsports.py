"""
JD Sports Multi-Collection Ingestion Pipeline
Ingests Nike footwear from JD Sports US across 3 target search collections:
1) Nike Air Max (Query: nike air max) -> ~254 products
2) Nike Air Force (Query: nike air force) -> ~155 products
3) Nike Dunk Low (Query: nike dunk low) -> ~105 products

Harvests all search page listings, scrapes hydrated JSON-LD ProductGroup payloads via Firecrawl,
normalizes multi-tier sizing and sibling colorway swatches, validates tri-field pricing,
and persists atomically into storage/db/jdsports/products/.
"""
import os
import sys
import re
import json
import time
import hashlib
from typing import Dict, Any, List, Optional, Tuple, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx
from lxml import html as lxml_html

sys.path.insert(0, r"c:\Users\Administrator\WorkPlace\dropship-scraper-portable-20260905\product-updater")
os.chdir(r"c:\Users\Administrator\WorkPlace\dropship-scraper-portable-20260905\product-updater")

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from storage.forex import get_usd_to_inr_rate
from storage.validator import validate_product
from storage.db import save_product, build_and_save_index, generate_product_id
from stores.jdsports.inflow import (
    classify_sizing_category,
    determine_gender,
    parse_and_format_size,
    generate_description_html,
    parse_product_payload
)

FIRECRAWL_API_KEY = "fc-359e2315bf4942a48f2bf46f237176b9"
FIRECRAWL_API_URL = "https://api.firecrawl.dev/v1/scrape"
CACHE_DIR = "scratch/jd_raw_pdp"

TARGET_COLLECTIONS = [
    {
        "name": "Nike Air Max",
        "group": "nike-air-max",
        "base_url": "https://www.jdsports.com/search?query=nike+air+max",
        "max_pages": 4
    },
    {
        "name": "Nike Air Force",
        "group": "nike-air-force",
        "base_url": "https://www.jdsports.com/search?query=nike%20air%20force",
        "max_pages": 3
    },
    {
        "name": "Nike Dunk Low",
        "group": "nike-dunk",
        "base_url": "https://www.jdsports.com/search?query=nike%20dunk%20low",
        "max_pages": 3
    }
]

def firecrawl_scrape_page(url: str, formats: List[str] = ["rawHtml", "html"]) -> Optional[Dict[str, Any]]:
    """Fetch URL content via Firecrawl API with retry logic."""
    headers = {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "url": url,
        "formats": formats
    }
    for attempt in range(3):
        try:
            with httpx.Client(timeout=90.0) as client:
                resp = client.post(FIRECRAWL_API_URL, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("success"):
                        return data.get("data", {})
                elif resp.status_code in (429, 502, 503, 504):
                    time.sleep(3.0 * (attempt + 1))
        except Exception as e:
            time.sleep(2.0 * (attempt + 1))
    return None

def harvest_collection_links(collection: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Harvest all distinct product PDP URLs across search pagination pages."""
    name = collection["name"]
    group = collection["group"]
    base_url = collection["base_url"]
    max_pages = collection["max_pages"]

    print(f"\n========================================================================", flush=True)
    print(f"HARVESTING SEARCH LISTINGS: {name.upper()}", flush=True)
    print(f"========================================================================", flush=True)

    discovered_urls = {}
    
    for page in range(1, max_pages + 1):
        page_url = base_url if page == 1 else f"{base_url}&page={page}"
        print(f"Scraping {name} Page {page}: {page_url}...", flush=True)
        
        scrape_data = firecrawl_scrape_page(page_url, formats=["html", "rawHtml"])
        if not scrape_data:
            print(f"  ⚠️ Failed to scrape page {page}", flush=True)
            continue

        raw_html_str = scrape_data.get("rawHtml") or scrape_data.get("html") or ""
        pdp_links = set(re.findall(r'https://www\.jdsports\.com/pdp/[^"\'>\s]+', raw_html_str))
        
        # Also extract relative PDP links
        rel_links = set(re.findall(r'href=[\'"](/pdp/[^"\'\s>]+)[\'"]', raw_html_str))
        for r_link in rel_links:
            pdp_links.add(f"https://www.jdsports.com{r_link}")

        new_count = 0
        for link in pdp_links:
            # Filter to legitimate product PDPs
            if "/pdp/" in link and ("prod" in link or re.search(r'/[A-Z0-9]{5,}/', link)):
                # Canonicalize URL by stripping query parameters
                clean_url = link.split("?")[0]
                if clean_url not in discovered_urls:
                    discovered_urls[clean_url] = {
                        "url": clean_url,
                        "collection": group,
                        "group_name": name
                    }
                    new_count += 1

        print(f"  Page {page} yielded {len(pdp_links)} total links ({new_count} new distinct products). Cumulative: {len(discovered_urls)}", flush=True)
        if new_count == 0 and page > 1:
            print(f"  No new products on page {page}, concluding pagination for {name}.", flush=True)
            break

    print(f"✅ Total Discovered Products for {name}: {len(discovered_urls)}", flush=True)
    return list(discovered_urls.values())

def extract_product_group_and_breadcrumbs(raw_html_str: str) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """Robust extraction of ProductGroup and BreadcrumbList JSON schemas from HTML scripts."""
    if not raw_html_str:
        return None, []
    
    try:
        tree = lxml_html.fromstring(raw_html_str)
        scripts = tree.xpath("//script/text()")
    except Exception:
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', raw_html_str, re.DOTALL)

    product_group = None
    breadcrumbs = []
    
    for s in scripts:
        s_clean = s.strip()
        if not s_clean:
            continue
        if '"@type":"ProductGroup"' in s_clean or '"@type": "ProductGroup"' in s_clean:
            try:
                parsed = json.loads(s_clean)
                if parsed.get("@type") == "ProductGroup":
                    product_group = parsed
            except Exception:
                m = re.search(r'(\{.*"@type"\s*:\s*"ProductGroup".*\})', s_clean, re.DOTALL)
                if m:
                    try:
                        parsed = json.loads(m.group(1))
                        if parsed.get("@type") == "ProductGroup":
                            product_group = parsed
                    except Exception:
                        pass

        if '"@type":"BreadcrumbList"' in s_clean or '"@type": "BreadcrumbList"' in s_clean:
            try:
                parsed = json.loads(s_clean)
                if parsed.get("@type") == "BreadcrumbList":
                    for el in parsed.get("itemListElement", []):
                        if isinstance(el, dict) and el.get("name"):
                            breadcrumbs.append(el["name"])
            except Exception:
                pass

    return product_group, breadcrumbs

def parse_and_expand_pdp(
    pdp_item: Dict[str, Any],
    forex_rate: float,
    scrape_data: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Parse a scraped JD Sports PDP HTML and extract all sibling colorway products
    with their individual size variant arrays.
    """
    url = pdp_item["url"]
    collection = pdp_item["collection"]
    group_name = pdp_item.get("group_name", collection)

    if not scrape_data:
        # Check cache first
        url_hash = hashlib.md5(url.encode()).hexdigest()
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache_file = os.path.join(CACHE_DIR, f"{url_hash}.json")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    scrape_data = json.load(f)
            except Exception:
                scrape_data = None

        if not scrape_data:
            scrape_data = firecrawl_scrape_page(url, formats=["rawHtml", "html"])
            if scrape_data:
                try:
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump(scrape_data, f)
                except Exception:
                    pass

    if not scrape_data:
        return []

    raw_html_str = scrape_data.get("rawHtml") or scrape_data.get("html") or ""
    if not raw_html_str:
        return []

    product_group_ld, breadcrumbs = extract_product_group_and_breadcrumbs(raw_html_str)

    # 2. Extract DOM images, title, and buttons if JSON-LD missing or incomplete
    dom_title = ""
    try:
        tree = lxml_html.fromstring(raw_html_str)
        h1_nodes = tree.xpath("//h1")
        if h1_nodes:
            dom_title = h1_nodes[0].text_content().strip()
    except Exception:
        tree = None

    products_to_save = []
    
    if product_group_ld:
        # Disaggregate variants by colorway
        colors = {}
        for v in product_group_ld.get("hasVariant", []):
            c = v.get("color") or "Standard"
            if c not in colors:
                colors[c] = []
            colors[c].append(v)

        for c_name, v_list in colors.items():
            first_v = v_list[0]
            v_url = first_v.get("offers", {}).get("url") if isinstance(first_v.get("offers"), dict) else url
            v_img = first_v.get("image")
            
            c_imgs = []
            for v in v_list:
                img = v.get("image")
                if img and img not in c_imgs:
                    c_imgs.append(img)

            sub_pg = {
                "@type": "ProductGroup",
                "name": product_group_ld.get("name"),
                "productGroupID": product_group_ld.get("productGroupID"),
                "color": c_name,
                "description": first_v.get("description"),
                "hasVariant": v_list,
                "images": c_imgs if c_imgs else ([v_img] if v_img else []),
                "source_url": v_url or url,
                "url": v_url or url,
                "breadcrumbs": breadcrumbs
            }
            parsed_prod = parse_product_payload(sub_pg, forex_rate, collection)
            if parsed_prod:
                groups = set(parsed_prod.get("groups", []))
                groups.add(collection)
                groups.add("shoes")
                groups.add("footwear")
                parsed_prod["groups"] = sorted(list(groups))
                products_to_save.append(parsed_prod)

    # Fallback to direct DOM parsing if no JSON-LD ProductGroup
    if not products_to_save and dom_title and tree is not None:
        size_buttons = tree.xpath("//button")
        dom_variants = []
        
        # Try finding price
        price_nodes = tree.xpath("//*[contains(text(), '$')]/text()")
        dom_price_usd = 0.0
        for pn in price_nodes:
            m = re.search(r'\$(\d+(?:\.\d{2})?)', pn.strip())
            if m:
                cand_p = float(m.group(1))
                if cand_p > 30.0:
                    dom_price_usd = cand_p
                    break
        if dom_price_usd <= 0:
            dom_price_usd = 150.0

        # Images
        img_srcs = tree.xpath("//img/@src")
        p_imgs = []
        seen_img = set()
        for src in img_srcs:
            if ("media.jdsports.com" in src or "finishline" in src) and not "logo" in src.lower():
                base_img = re.sub(r'\?.*$', '', src)
                if base_img not in seen_img:
                    seen_img.add(base_img)
                    p_imgs.append(src)

        tier = classify_sizing_category(dom_title, breadcrumbs)
        gender = determine_gender(dom_title, tier)

        for btn in size_buttons:
            btn_text = btn.text_content().strip()
            aria = btn.get("aria-label", "")
            cls = btn.get("class", "")
            disabled = btn.get("disabled") is not None or "disabled" in cls or "crossed" in cls
            
            if re.match(r'^\d+(\.\d+)?[CWY]?$', btn_text) or "size" in aria.lower():
                raw_size_clean = re.sub(r'^size\s*', '', aria if "size" in aria.lower() else btn_text, flags=re.I).strip()
                v_label, uk, eu, num_val = parse_and_format_size(raw_size_clean, tier, gender)
                v_title = f"{v_label} / UK {uk} - Standard"
                v_sku = hashlib.md5(f"{url}::{v_title}".encode()).hexdigest()[:12].upper()
                
                v_inr = float(round(dom_price_usd * forex_rate))
                dom_variants.append({
                    "id": None,
                    "sku": v_sku,
                    "title": v_title,
                    "option_values": [
                        {"option_name": "Size (US)", "name": v_label},
                        {"option_name": "Size (UK)", "name": f"UK {uk}"},
                        {"option_name": "Color", "name": "Standard"}
                    ],
                    "source_price": dom_price_usd,
                    "source_price_usd": dom_price_usd,
                    "price": f"{round(v_inr):.2f}",
                    "price_current": v_inr,
                    "currency": "INR",
                    "source_currency": "USD",
                    "available": not disabled,
                    "in_stock": not disabled,
                    "image_url": p_imgs[0] if p_imgs else None
                })

        if dom_variants:
            p_id = generate_product_id("jdsports", url)
            any_avail = any(v["in_stock"] for v in dom_variants)
            inr_price = float(round(dom_price_usd * forex_rate))

            product_record = {
                "id": p_id,
                "source_store": "jdsports",
                "brand": "Nike",
                "title": dom_title,
                "handle": re.sub(r'[^a-z0-9]+', '-', dom_title.lower()).strip('-'),
                "source_url": url,
                "url": url,
                "source_price": dom_price_usd,
                "current_price": inr_price,
                "price": inr_price,
                "availability": "in_stock" if any_avail else "out_of_stock",
                "is_active": any_avail,
                "images": p_imgs,
                "variants": dom_variants,
                "groups": [collection, "shoes", "footwear"],
                "tags": ["Nike", collection, "Footwear"],
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "last_verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            products_to_save.append(product_record)

    return products_to_save

def run_ingestion_pipeline():
    start_time = time.time()
    print("=" * 80, flush=True)
    print("JD SPORTS MULTI-COLLECTION INGESTION PIPELINE", flush=True)
    print("Target Collections: Nike Air Max (254), Nike Air Force (155), Nike Dunk Low (105)", flush=True)
    print("=" * 80, flush=True)

    forex_rate = get_usd_to_inr_rate()
    print(f"Current USD->INR Forex Rate: {forex_rate}\n", flush=True)

    # 1. Harvest all listing URLs
    all_targets = []
    for coll in TARGET_COLLECTIONS:
        targets = harvest_collection_links(coll)
        all_targets.extend(targets)

    # Deduplicate targets by canonical URL
    unique_targets = {}
    for t in all_targets:
        u = t["url"]
        if u not in unique_targets:
            unique_targets[u] = t

    target_list = list(unique_targets.values())
    print(f"\nTotal Unique JD Sports PDPs to Ingest: {len(target_list)}", flush=True)

    # 2. Ingest PDPs in parallel using ThreadPoolExecutor
    print("\n========================================================================", flush=True)
    print("INGESTING & EXPANDING PDP MATRICES CONCURRENTLY", flush=True)
    print("========================================================================", flush=True)

    saved_count = 0
    total_variants_count = 0
    errors_count = 0

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_item = {
            executor.submit(parse_and_expand_pdp, item, forex_rate): item
            for item in target_list
        }

        for idx, future in enumerate(as_completed(future_to_item), 1):
            item = future_to_item[future]
            try:
                products = future.result()
                if not products:
                    print(f"[{idx}/{len(target_list)}] ⚠️ No products parsed from {item['url']}", flush=True)
                    continue

                for p in products:
                    # Validate product schema
                    valid, status_sug, errs = validate_product(p)
                    if not valid:
                        print(f"[{idx}/{len(target_list)}] ❌ Validation error for {p.get('title')}: {errs}", flush=True)
                        errors_count += 1
                        continue

                    # Atomically save product
                    save_product(p)
                    saved_count += 1
                    total_variants_count += len(p.get("variants", []))

                print(f"[{idx}/{len(target_list)}] ✅ Ingested {len(products)} colorways ({sum(len(p.get('variants', [])) for p in products)} variants) from {products[0].get('title', '')[:40]}", flush=True)

            except Exception as e:
                print(f"[{idx}/{len(target_list)}] ❌ Exception ingesting {item['url']}: {e}", flush=True)
                errors_count += 1

    # 3. Build and save global DB index
    print("\n========================================================================", flush=True)
    print("REBUILDING CATALOG INDEX", flush=True)
    print("========================================================================", flush=True)
    index_map = build_and_save_index()
    
    elapsed = time.time() - start_time
    print(f"\n" + "=" * 80, flush=True)
    print("INGESTION SUMMARY", flush=True)
    print("=" * 80, flush=True)
    print(f"Total Unique PDPs Scraped:  {len(target_list)}", flush=True)
    print(f"Total JD Sports Products:   {saved_count}", flush=True)
    print(f"Total Variants Ingested:    {total_variants_count}", flush=True)
    print(f"Validation Errors:          {errors_count}", flush=True)
    print(f"Total Global Catalog in DB: {len(index_map)}", flush=True)
    print(f"Elapsed Time:               {elapsed:.1f}s", flush=True)
    print("=" * 80, flush=True)

if __name__ == "__main__":
    run_ingestion_pipeline()
