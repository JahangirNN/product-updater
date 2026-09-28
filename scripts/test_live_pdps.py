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
    # Select 2 products with shopify_handle or handle
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
        
        # 1. Price formatting (check for INR symbol and no .00 paise in display if ADR 0006)
        # Look for price in DOM
        has_price = bool(re.search(r'₹\s*[\d,]+', text)) or "price" in text.lower()
        has_fractional_paise = bool(re.search(r'₹\s*[\d,]+\.\d{2}', text))
        
        # 2. Add to cart button
        has_atc = "add-to-cart" in text.lower() or "add to cart" in text.lower() or 'name="add"' in text
        
        # 3. Media gallery / images
        has_gallery = "product-gallery" in text or "media-gallery" in text or "<img" in text
        
        # 4. Variant selector / options
        has_variants = "variant" in text.lower() or "option" in text.lower() or "color" in text.lower()
        
        # 5. Accordion / Specifications
        has_accordion = "size-guide-accordion" in text or "accordion" in text.lower()
        has_specs = "technical specifications" in text.lower() or "product specifications" in text.lower() or "material" in text.lower()

        print(f"\n[{status}] {brand.upper()}: {title[:35]} ({handle})")
        print(f"  URL: {url}")
        print(f"  Price in DOM: {has_price} | Fractional paise: {has_fractional_paise}")
        print(f"  Add to Cart Button: {has_atc}")
        print(f"  Media Gallery: {has_gallery}")
        print(f"  Variant Selector: {has_variants}")
        print(f"  Accordion: {has_accordion} | Specs: {has_specs}")
        
    except Exception as e:
        print(f"\n[ERR] {brand.upper()}: {title} -> {e}")
