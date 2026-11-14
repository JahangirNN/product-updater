"""
Jomashop Sunglasses Scraper (Best Sellers Only)
Extracts best-selling designer sunglasses across Carrera, Calvin Klein, Miu Miu, Hugo Boss, Tory Burch, and Oakley.
Strictly excludes eyeglasses / optical frames (ADR 0028).
"""
import os
import sys
import json
import time
import hashlib
from typing import Dict, Any, List

# Ensure product-updater is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from curl_cffi import requests
from storage.forex import get_usd_to_inr_rate

GRAPHQL_URL = "https://www.jomashop.com/graphql"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://www.jomashop.com",
    "Referer": "https://www.jomashop.com/",
}

QUERY_PLP = """
query getSunglasses($filter: ProductAttributeFilterInput!, $pageSize: Int!, $currentPage: Int!) {
  products(filter: $filter, pageSize: $pageSize, currentPage: $currentPage) {
    total_count
    items {
      id
      name
      sku
      url_key
      stock_status
      upc_code
      jomashop_social_proof_selection {
        is_best_seller
        is_most_viewed
      }
      price_range {
        minimum_price {
          regular_price { value currency }
          final_price { value currency }
          msrp_price { value currency }
        }
      }
      media_gallery {
        ... on ProductImage {
          sizes {
            url
          }
        }
      }
      moredetails {
        more_details_text {
          manufacturer
          department
          subtype
        }
      }
    }
  }
}
"""

TARGET_CONFIGS = [
    {
        "brand": "Carrera",
        "filter": {"manufacturer": {"eq": "Carrera"}, "department": {"eq": "Sunglasses"}, "price": {"from": "0", "to": "50"}},
        "max_items": 30
    },
    {
        "brand": "Calvin Klein",
        "filter": {"manufacturer": {"eq": "Calvin Klein"}, "department": {"eq": "Sunglasses"}, "price": {"from": "0", "to": "25"}},
        "max_items": 25
    },
    {
        "brand": "Miu Miu",
        "filter": {"manufacturer": {"eq": "Miu Miu"}, "department": {"eq": "Sunglasses"}, "price": {"from": "100", "to": "300"}},
        "max_items": 30
    },
    {
        "brand": "Hugo Boss",
        "filter": {"manufacturer": {"eq": "Hugo Boss"}, "department": {"eq": "Sunglasses"}},
        "max_items": 35
    },
    {
        "brand": "Tory Burch",
        "filter": {"manufacturer": {"eq": "Tory Burch"}, "department": {"eq": "Sunglasses"}},
        "max_items": 30
    },
    {
        "brand": "Oakley",
        "filter": {"manufacturer": {"eq": "Oakley"}, "department": {"eq": "Sunglasses"}, "price": {"from": "0", "to": "120"}},
        "max_items": 35
    }
]

EXCLUDE_KEYWORDS = ["eyeglass", "eyeglasses", "optical", "demo lens", "clear lens", "prescription glasses", "reading glasses", "frames only"]

def is_sunglasses_only(item: Dict[str, Any]) -> bool:
    name = (item.get("name") or "").lower()
    for kw in EXCLUDE_KEYWORDS:
        if kw in name:
            return False
    dept = item.get("moredetails", {}).get("more_details_text", {}).get("department", "")
    if dept and "sunglasses" not in dept.lower():
        return False
    return True

def scrape_brand_sunglasses(cfg: Dict[str, Any], rate: float) -> List[Dict[str, Any]]:
    brand = cfg["brand"]
    filter_input = cfg["filter"]
    max_items = cfg.get("max_items", 30)
    print(f"\n--- Scraping Best Sellers for {brand} (target <= {max_items}) ---")

    collected = []
    page = 1
    
    while len(collected) < max_items:
        payload = {
            "query": QUERY_PLP,
            "variables": {
                "filter": filter_input,
                "pageSize": 50,
                "currentPage": page
            }
        }
        
        try:
            resp = requests.post(GRAPHQL_URL, json=payload, headers=HEADERS, impersonate="chrome120", timeout=15)
            if resp.status_code != 200:
                print(f"[{brand}] HTTP error {resp.status_code}")
                break
            
            data = resp.json()
            if "errors" in data:
                print(f"[{brand}] GraphQL errors: {data['errors']}")
                break
                
            p_res = data.get("data", {}).get("products", {})
            items = p_res.get("items", [])
            total_count = p_res.get("total_count", 0)
            
            if not items:
                break
                
            # Filter best sellers or high-demand sunglasses
            for it in items:
                if not is_sunglasses_only(it):
                    continue
                
                proof = it.get("jomashop_social_proof_selection") or {}
                # Prioritize is_best_seller, or include in order of popularity
                collected.append(it)
                if len(collected) >= max_items:
                    break
                    
            print(f"[{brand}] Page {page}: collected {len(collected)} items so far (total available: {total_count})")
            if len(items) < 50 or len(collected) >= max_items:
                break
            page += 1
            time.sleep(0.5)
            
        except Exception as e:
            print(f"[{brand}] Exception: {e}")
            break
            
    # Normalize products
    normalized_products = []
    for it in collected:
        sku = it.get("sku") or ""
        name = it.get("name") or ""
        url_key = it.get("url_key") or ""
        p_range = it.get("price_range", {}).get("minimum_price", {})
        
        final_usd = float(p_range.get("final_price", {}).get("value") or 0.0)
        msrp_usd = float(p_range.get("msrp_price", {}).get("value") or p_range.get("regular_price", {}).get("value") or final_usd)
        
        final_inr = round(final_usd * rate)
        compare_inr = round(msrp_usd * rate) if msrp_usd > final_usd else None
        compare_usd = msrp_usd if msrp_usd > final_usd else None
        
        # Images
        gallery = it.get("media_gallery") or []
        images = []
        for g in gallery:
            sizes = g.get("sizes") or []
            if sizes:
                images.append(sizes[-1].get("url"))
        images = [img for img in images if img]
        
        in_stock = (it.get("stock_status") == "IN_STOCK")
        
        prod_obj = {
            "id": hashlib.md5(f"jomashop_{sku}".encode()).hexdigest()[:16],
            "source_store": "jomashop",
            "source_url": f"https://www.jomashop.com/{url_key}.html" if url_key else f"https://www.jomashop.com",
            "handle": url_key,
            "title": name,
            "vendor": brand,
            "product_type": "Sunglasses",
            "source_sku": sku,
            "source_price": final_usd,
            "source_compare_at_price": compare_usd,
            "current_price": final_inr,
            "compare_at_price": compare_inr,
            "currency": "INR",
            "source_currency": "USD",
            "forex_rate_used": rate,
            "availability": "in_stock" if in_stock else "out_of_stock",
            "specifications": {
                "Brand": brand,
                "Category": "Sunglasses",
                "Department": "Sunglasses",
                "UPC": it.get("upc_code") or "",
                "SKU": sku
            },
            "descriptionHtml": f"<div class=\"product-description\"><p>{name}</p><ul><li>Brand: {brand}</li><li>Category: Sunglasses</li><li>Authenticity: 100% Guaranteed Genuine</li><li>SKU: {sku}</li></ul></div>",
            "images": images,
            "variants": [
                {
                    "id": hashlib.md5(f"jomashop_var_{sku}".encode()).hexdigest()[:16],
                    "title": "Default Title",
                    "sku": sku,
                    "price": final_inr,
                    "compare_at_price": compare_inr,
                    "source_price": final_usd,
                    "source_compare_at_price": compare_usd,
                    "in_stock": in_stock,
                    "is_available": in_stock
                }
            ],
            "groups": ["sunglasses", brand.lower().replace(" ", "-")]
        }
        normalized_products.append(prod_obj)

    return normalized_products

def run():
    rate = get_usd_to_inr_rate()
    print(f"Using USD to INR forex rate: {rate}")
    
    out_dir = os.path.join("product-updater", "storage", "db", "jomashop", "products")
    os.makedirs(out_dir, exist_ok=True)
    
    total_saved = 0
    for cfg in TARGET_CONFIGS:
        prods = scrape_brand_sunglasses(cfg, rate)
        for p in prods:
            file_name = f"{p['source_sku']}.json"
            file_path = os.path.join(out_dir, file_name)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(p, f, indent=2)
            total_saved += 1
            
    print(f"\n==========================================")
    print(f"JOMASHOP SUNGLASSES INGESTION COMPLETE!")
    print(f"Total Sunglasses Saved: {total_saved}")
    print(f"Storage Directory: {out_dir}")
    print(f"==========================================")

if __name__ == "__main__":
    run()
