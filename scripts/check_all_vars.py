import json

with open("product-updater/storage/db/sephora/products/08702e1da9320ab5.json", encoding="utf-8") as f:
    p = json.load(f)

for v in p.get("variants", []):
    print(f"SKU: {v.get('sku')}, variation_value: {v.get('variation_value')}, size: {v.get('size')}, price: {v.get('price_inr')}")
