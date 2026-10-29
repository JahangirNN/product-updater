import os
import sys
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_taxonomy import prepare_product_set_payload, resolve_options_and_variants

with open(os.path.join(PROJECT_ROOT, "storage", "db", "coach", "products", "0f73f4eea686b114.json"), "r", encoding="utf-8") as f:
    prod = json.load(f)

print("Product title:", prod.get("title"))
print("Product type:", prod.get("product_type"))
print("Handle:", prod.get("handle"))
print("Variants count:", len(prod.get("variants", [])))

opts, vars_out = resolve_options_and_variants(prod, 95.0, 100.0, None)
print("\nResolved Options:", json.dumps(opts, indent=2))
print(f"\nResolved Variants Count: {len(vars_out)}")
for v in vars_out[:5]:
    print("  Variant:", v.get("optionValues"), "| file:", v.get("file"))
