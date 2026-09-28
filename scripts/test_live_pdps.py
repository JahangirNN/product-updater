import os
import sys
import json
import re
import httpx

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from scripts.audit_luxury_bags_catalog import get_luxury_bag_products

catalog = get_luxury_bag_products()
client = httpx.Client(follow_redirects=True, timeout=15.0)

print("=" * 80)
print("TESTING LIVE PDP RENDERING ACROSS COACH, JW PEI, AND MICHAEL KORS")
print("=" * 80)

samples = []
for brand in ["coach", "jwpei", "michaelkors"]:
    prods = [p for p in catalog[brand] if p.get("shopify_product_id")]
    for p in prods[:2]:
        handle = p.get("shopify_handle") or p.get("handle")
        samples.append((brand, p.get("title"), handle))

for brand, title, handle in samples:
    url = f"https://therareavenue.com/products/{handle}"
    try:
        r = client.get(url)
        status = r.status_code
        text = r.text
        
        if status == 200:
            has_price = bool(re.search(r'₹\s*[\d,]+', text))
            has_fractional_paise = bool(re.search(r'₹\s*[\d,]+\.\d{2}', text))
            has_atc = "add to cart" in text.lower() or 'name="add"' in text
            has_gallery = "product-gallery" in text or "media-gallery" in text or "<img" in text
            has_variants = "variant-picker" in text or "option-selector" in text or "color" in text.lower()
            has_accordion = "size-guide-accordion" in text
            has_specs = "product specifications" in text.lower() or "silhouette" in text.lower()

            print(f"\n[{status}] {brand.upper()}: {title[:35]} ({handle})")
            print(f"  URL: {url}")
            print(f"  Price in DOM: {has_price} | Fractional paise: {has_fractional_paise}")
            print(f"  Add to Cart Button: {has_atc}")
            print(f"  Media Gallery: {has_gallery}")
            print(f"  Variant Selector: {has_variants}")
            print(f"  Accordion: {has_accordion} | Specs: {has_specs}")
        else:
            print(f"\n[{status}] {brand.upper()}: {title[:35]} ({handle})")
            print(f"  URL: {url}")
            print(f"  Status: HTTP {status} (Unpublished to Online Store sales channel)")
        
    except Exception as e:
        print(f"\n[ERR] {brand.upper()}: {title} -> {e}")
