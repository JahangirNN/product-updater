import json, glob

for pf in glob.glob('product-updater/storage/db/sephora/products/*.json')[:5]:
    with open(pf, 'r', encoding='utf-8') as f:
        p = json.load(f)
        for v in p.get('variants', [])[:2]:
            print(f"SKU: {v.get('sku')} | title: {v.get('title')} | val: {v.get('variation_value')} | size: {v.get('size')} | price_inr: {v.get('price_inr')} | usd: {v.get('source_price_usd')}")
