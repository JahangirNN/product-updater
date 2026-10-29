import os
import sys
import json
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_taxonomy import prepare_product_set_payload

with open("storage/db/coach/products/0027f9241db46df8.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("Title:", data.get("title"))
print("DB Variants count:", len(data.get("variants", [])))
for v in data.get("variants", []):
    print("  DB Var:", v.get("sku"), "|", v.get("title"), "|", v.get("in_stock"), "|", v.get("image_url"))

payload = prepare_product_set_payload(data)
print("\nPayload productOptions:", payload.get("productOptions"))
print("Payload variants count:", len(payload.get("variants", [])))
for v in payload.get("variants", []):
    print("  Payload Var:", v.get("sku"), "|", v.get("optionValues"), "|", v.get("file"))
