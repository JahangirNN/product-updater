#!/usr/bin/env python3
"""
Sephora 14-Brand Fast Catalog Harvester
Queries Sephora's production discovery API (sephora.cnstrc.com) to harvest
canonical product URLs, IDs, titles, default SKUs, and base pricing across the 14 target brands.
Outputs structured JSON to storage/sephora_discovered_urls.json.
"""

import os
import sys
import json
import time
import urllib.parse
from typing import Dict, Any, List
from curl_cffi import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_DIR = os.path.join(PROJECT_ROOT, "storage")
OUTPUT_PATH = os.path.join(STORAGE_DIR, "sephora_discovered_urls.json")

CONSTRUCTOR_KEY = "u7PNVQx-prod-en-us"
SEARCH_BASE_URL = "https://sephora.cnstrc.com/search/{query}"

TARGET_BRANDS = [
    {"name": "Summer Fridays", "query": "Summer Fridays", "match_terms": ["summer fridays"]},
    {"name": "Gisou", "query": "Gisou", "match_terms": ["gisou"]},
    {"name": "Haus Labs", "query": "Haus Labs", "match_terms": ["haus labs"]},
    {"name": "Patrick Ta", "query": "Patrick Ta", "match_terms": ["patrick ta"]},
    {"name": "Saie", "query": "Saie", "match_terms": ["saie"]},
    {"name": "Tower 28", "query": "Tower 28", "match_terms": ["tower 28"]},
    {"name": "Merit", "query": "Merit", "match_terms": ["merit"]},
    {"name": "Westman Atelier", "query": "Westman Atelier", "match_terms": ["westman atelier"]},
    {"name": "Kosas", "query": "Kosas", "match_terms": ["kosas"]},
    {"name": "Rhode", "query": "Rhode", "match_terms": ["rhode"]},
    {"name": "Glossier", "query": "Glossier", "match_terms": ["glossier"]},
    {"name": "Makeup by Mario", "query": "Makeup by Mario", "match_terms": ["makeup by mario"]},
    {"name": "Hourglass", "query": "Hourglass", "match_terms": ["hourglass"]},
    {"name": "REFY", "query": "REFY", "match_terms": ["refy"]},
]

def harvest_brand_products(brand_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Harvest all products belonging to a brand from Sephora's search catalog API."""
    name = brand_info["name"]
    query = brand_info["query"]
    match_terms = [t.lower() for t in brand_info["match_terms"]]
    
    encoded_q = urllib.parse.quote(query)
    url = f"{SEARCH_BASE_URL.format(query=encoded_q)}?key={CONSTRUCTOR_KEY}&num_results_per_page=100"
    
    products_map = {}
    
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=45)
            if r.status_code != 200:
                print(f"[{name}] API Error: HTTP {r.status_code}")
                time.sleep(1.0)
                continue
                
            data = r.json()
            results = data.get("response", {}).get("results", [])
            
            for item in results:
                d = item.get("data", {})
                pid = d.get("id")
                raw_url = d.get("url")
                brand_name = d.get("brandName", "")
                
                # Verify brand name matches target
                b_lower = brand_name.lower()
                if not any(term in b_lower for term in match_terms):
                    continue
                    
                if pid and raw_url:
                    clean_url = "https://www.sephora.com" + raw_url.split("?")[0]
                    if pid not in products_map:
                        products_map[pid] = {
                            "id": pid,
                            "brand": name,
                            "brand_name_raw": brand_name,
                            "title": item.get("value"),
                            "url": clean_url,
                            "default_sku": d.get("currentSku", {}).get("skuId"),
                            "num_variants": d.get("numberOfVariants", 1),
                            "price_usd": d.get("currentSku", {}).get("listPriceFloat"),
                            "image_url": d.get("image_url")
                        }
            if products_map:
                break
        except Exception as e:
            if attempt == 2:
                print(f"[{name}] Exception during harvest (attempt {attempt+1}): {e}")
            time.sleep(1.5)
        
    return list(products_map.values())

def main():
    print("=" * 80)
    print("SEPHORA 14-BRAND CATALOG HARVESTER")
    print("=" * 80)
    
    os.makedirs(STORAGE_DIR, exist_ok=True)
    all_products = []
    brand_breakdown = {}
    
    for b in TARGET_BRANDS:
        b_name = b["name"]
        t0 = time.perf_counter()
        prods = harvest_brand_products(b)
        elapsed = time.perf_counter() - t0
        all_products.extend(prods)
        brand_breakdown[b_name] = len(prods)
        print(f"• {b_name:<18}: {len(prods):<3} products harvested ({elapsed:.2f}s)")
        time.sleep(0.2)
        
    print("-" * 80)
    print(f"TOTAL HARVESTED PRODUCTS ACROSS ALL 14 BRANDS: {len(all_products)}")
    print("=" * 80)
    
    manifest = {
        "harvested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_products": len(all_products),
        "brands_count": len(TARGET_BRANDS),
        "brand_breakdown": brand_breakdown,
        "products": all_products
    }
    
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"SUCCESS: Saved {len(all_products)} products to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
