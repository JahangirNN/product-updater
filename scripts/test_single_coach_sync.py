import os
import sys
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_sync import upsert_product_to_shopify

with open(os.path.join(PROJECT_ROOT, "storage", "db", "coach", "products", "0f73f4eea686b114.json"), "r", encoding="utf-8") as f:
    prod = json.load(f)

print("Upserting Coach Teri Mini Crossbody to Shopify...")
ok, p_node, err = upsert_product_to_shopify(prod, 95.0)
print(f"Upsert success: {ok}")
print(f"Product node: {p_node}")
print(f"Error: {err}")
