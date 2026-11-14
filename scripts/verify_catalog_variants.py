import json
import sys

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

with open('product-updater/frontend/public/data/catalog.json', 'r', encoding='utf-8') as f:
    cat = json.load(f)

for brand in ['Saie', 'Gisou', 'Glossier', 'Hourglass', 'COACH', 'Kate Spade']:
    for p in cat:
        if brand.lower() in p.get('vendor', '').lower() or brand.lower() in p.get('store_display', '').lower():
            print(f"=== {p.get('vendor')} | {p.get('title')[:40]} ===")
            print(f"  Parent: current_price=₹{p.get('current_price')} | source_price=${p.get('source_price')}")
            print(f"  Ranges: inr={p.get('price_range_inr')} | usd={p.get('price_range_usd')}")
            for v in p.get('variants', [])[:3]:
                print(f"    Variant: {v.get('title')[:35]} | price=₹{v.get('price')} | source=${v.get('source_price')}")
            break
