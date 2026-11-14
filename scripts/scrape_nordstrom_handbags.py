"""
Nordstrom & Nordstrom Rack Handbags Scraper
Ingests luxury handbags across Tory Burch (Nordstrom), Marc Jacobs (Rack), and Kurt Geiger London (Rack).
Extracts complete product matrix, colorways, high-res images, and stock from window.__INITIAL_CONFIG__.
Pure functions only (ADR 0004, ADR 0005, ADR 0028).
"""
import os
import sys
import json
import time
import hashlib
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from camoufox.sync_api import Camoufox
from storage.forex import get_usd_to_inr_rate

TARGETS = [
    {
        "store_slug": "nordstrom",
        "brand_name": "Tory Burch",
        "pages": [
            "https://www.nordstrom.com/sr?origin=keywordsearch&keyword=tory%20burch&position=1&typein=tory%20burch&sort=PriceLowToHigh&filterByPrice=0-200&filterByPrice=200-300&filterByPrice=300-400&filterByProductType=accessories_handbags&page=1",
            "https://www.nordstrom.com/sr?origin=keywordsearch&keyword=tory%20burch&position=1&typein=tory%20burch&sort=PriceLowToHigh&filterByPrice=0-200&filterByPrice=200-300&filterByPrice=300-400&filterByProductType=accessories_handbags&page=2"
        ]
    },
    {
        "store_slug": "nordstromrack",
        "brand_name": "Marc Jacobs",
        "pages": [
            "https://www.nordstromrack.com/search?origin=keywordsearch&keyword=handbags&filterByBrand=marc-jacobs&filterByProductType=accessories_handbags&page=1",
            "https://www.nordstromrack.com/search?origin=keywordsearch&keyword=handbags&filterByBrand=marc-jacobs&filterByProductType=accessories_handbags&page=2"
        ]
    },
    {
        "store_slug": "nordstromrack",
        "brand_name": "Kurt Geiger London",
        "pages": [
            "https://www.nordstromrack.com/search?origin=keywordsearch&keyword=handbags&filterByBagSize=small&filterByBagSize=medium&filterByBagSize=extra-large&filterByBrand=kurt-geiger-london&filterByPrice=0-50&filterByPrice=50-100&filterByPrice=100-200&filterByProductType=accessories_handbags"
        ]
    }
]

def parse_page_config(html: str) -> Dict[str, Any]:
    idx = html.find("window.__INITIAL_CONFIG__ =")
    if idx == -1:
        return {}
    raw_sub = html[idx + len("window.__INITIAL_CONFIG__ ="):].strip()
    try:
        config_data, _ = json.JSONDecoder().raw_decode(raw_sub)
        return config_data.get("productResults", {})
    except Exception as e:
        print("JSON parse error:", e)
        return {}

def extract_products_from_results(p_res: Dict[str, Any], store_slug: str, target_brand: str, rate: float) -> List[Dict[str, Any]]:
    p_by_id = p_res.get("productsById", {})
    extracted = []

    for pid, p in p_by_id.items():
        title = p.get("copyProductTitle") or ""
        brand = p.get("labelDisplayName") or p.get("sellingBrand") or target_brand
        if brand.upper() in ["NORDSTROM", "NORDSTROM_RACK", "NORDSTROM RACK"]:
            brand = target_brand
            
        handle = p.get("webPathAlias") or f"product-{pid}"
        
        props = p.get("propositions", [])
        prop0 = props[0] if props else {}
        
        # Prices
        sell_range = prop0.get("sellingRetailPriceRange", {})
        comp_range = prop0.get("compareAtRetailPriceRange", {}) or prop0.get("baseRetailPriceRange", {})
        
        try:
            price_usd = float(sell_range.get("min") or sell_range.get("max") or 0.0)
        except (ValueError, TypeError):
            price_usd = 0.0
            
        try:
            comp_usd = float(comp_range.get("max") or comp_range.get("min") or 0.0)
        except (ValueError, TypeError):
            comp_usd = price_usd

        if comp_usd <= price_usd:
            comp_usd = None
            
        price_inr = round(price_usd * rate)
        comp_inr = round(comp_usd * rate) if comp_usd else None
        
        # Stock
        avail = prop0.get("availability", {})
        ship_qty = int(avail.get("shipQuantity", 0) or 0)
        salability = prop0.get("salability", {}).get("status", "")
        in_stock = (salability == "SELLABLE") and (ship_qty > 0)
        
        # Colorways & Images
        images = []
        variants = []
        core_prods = p.get("coreProducts", [])
        for cp in core_prods:
            choices = cp.get("coreChoices", [])
            for c in choices:
                c_id = c.get("coreChoiceId") or str(pid)
                c_color = c.get("displayColorDescription") or "Default"
                c_images = []
                for s in c.get("orderedShots", []):
                    img_url = s.get("imageUrl")
                    if img_url and img_url not in c_images:
                        c_images.append(img_url)
                        if img_url not in images:
                            images.append(img_url)
                            
                variants.append({
                    "id": hashlib.md5(f"{pid}_{c_id}".encode()).hexdigest()[:16],
                    "title": c_color.title() if c_color != "Default" else "Default Title",
                    "sku": f"{store_slug.upper()}-{pid}-{c_id}",
                    "price": price_inr,
                    "compare_at_price": comp_inr,
                    "source_price": price_usd,
                    "source_compare_at_price": comp_usd,
                    "in_stock": in_stock,
                    "is_available": in_stock,
                    "color": c_color.title(),
                    "image": c_images[0] if c_images else (images[0] if images else None)
                })

        if not variants:
            variants.append({
                "id": hashlib.md5(f"{pid}_default".encode()).hexdigest()[:16],
                "title": "Default Title",
                "sku": f"{store_slug.upper()}-{pid}",
                "price": price_inr,
                "compare_at_price": comp_inr,
                "source_price": price_usd,
                "source_compare_at_price": comp_usd,
                "in_stock": in_stock,
                "is_available": in_stock
            })

        domain = "www.nordstrom.com" if store_slug == "nordstrom" else "www.nordstromrack.com"
        source_url = f"https://{domain}/s/{handle}/{pid}"
        
        prod_doc = {
            "id": hashlib.md5(f"{store_slug}_{pid}".encode()).hexdigest()[:16],
            "source_store": store_slug,
            "source_url": source_url,
            "handle": handle,
            "title": title,
            "vendor": brand,
            "product_type": "Handbags",
            "source_sku": f"{store_slug.upper()}-{pid}",
            "source_price": price_usd,
            "source_compare_at_price": comp_usd,
            "current_price": price_inr,
            "compare_at_price": comp_inr,
            "currency": "INR",
            "source_currency": "USD",
            "forex_rate_used": rate,
            "availability": "in_stock" if in_stock else "out_of_stock",
            "specifications": {
                "Brand": brand,
                "Category": "Handbags",
                "Item Number": str(pid),
                "Source Store": "Nordstrom" if store_slug == "nordstrom" else "Nordstrom Rack"
            },
            "descriptionHtml": f"<div class=\"product-description\"><p>{title}</p><ul><li>Brand: {brand}</li><li>Category: Luxury Handbag</li><li>Store: {'Nordstrom' if store_slug == 'nordstrom' else 'Nordstrom Rack'}</li><li>Item Number: {pid}</li></ul></div>",
            "images": images,
            "variants": variants,
            "groups": ["handbags", brand.lower().replace(" ", "-")]
        }
        extracted.append(prod_doc)

    return extracted

def run():
    rate = get_usd_to_inr_rate()
    print(f"USD to INR Rate: {rate}")
    
    total_saved = {
        "nordstrom": 0,
        "nordstromrack": 0
    }
    
    with Camoufox(headless=True) as browser:
        page = browser.new_page()
        
        for tgt in TARGETS:
            s_slug = tgt["store_slug"]
            b_name = tgt["brand_name"]
            out_dir = os.path.join("product-updater", "storage", "db", s_slug, "products")
            os.makedirs(out_dir, exist_ok=True)
            
            for url in tgt["pages"]:
                print(f"\n[{s_slug.upper()} - {b_name}] Navigating to: {url}")
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=45000)
                except Exception as e:
                    print(f"Goto note: {e}")
                    
                for attempt in range(15):
                    page.wait_for_timeout(2000)
                    html = page.content()
                    if "window.__INITIAL_CONFIG__ =" in html and len(html) > 500000:
                        print(f"Kasada cleared on attempt {attempt+1}! Len={len(html)}")
                        break
                        
                p_res = parse_page_config(html)
                prods = extract_products_from_results(p_res, s_slug, b_name, rate)
                print(f"[{s_slug.upper()} - {b_name}] Extracted {len(prods)} products from this page.")
                
                for p in prods:
                    fn = f"{p['source_sku']}.json"
                    fp = os.path.join(out_dir, fn)
                    with open(fp, "w", encoding="utf-8") as f:
                        json.dump(p, f, indent=2)
                    total_saved[s_slug] += 1
                    
                time.sleep(2)

    print("\n==========================================")
    print("NORDSTROM & RACK SCRAPING COMPLETE!")
    print(f"Nordstrom products saved: {total_saved['nordstrom']}")
    print(f"Nordstrom Rack products saved: {total_saved['nordstromrack']}")
    print("==========================================")

if __name__ == "__main__":
    run()
