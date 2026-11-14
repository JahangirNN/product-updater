import os
import sys

PROJECT_ROOT = "product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_taxonomy import prepare_product_set_payload
import json

# Load one test product: Saie Dew Blush (20 variants, multi-price, multi-color, multi-size)
p_path = "product-updater/storage/db/sephora/products/08702e1da9320ab5.json"
with open(p_path, encoding="utf-8") as f:
    p = json.load(f)

payload = prepare_product_set_payload(p, forex_rate=86.5)
print("Title:", payload.get("title"))
print("Vendor:", payload.get("vendor"))
print("Product Type:", payload.get("productType"))
print("Tags:", payload.get("tags")[:8])
print("Product Options:", payload.get("productOptions"))
print("Variants Count:", len(payload.get("variants", [])))
print("Sample Variant 0:")
print(json.dumps(payload.get("variants", [])[0], indent=2))
if len(payload.get("variants", [])) > 1:
    print("Sample Variant 1:")
    print(json.dumps(payload.get("variants", [])[1], indent=2))
