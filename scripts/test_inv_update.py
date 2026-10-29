import os
import sys
import glob
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_sync import upsert_product_to_shopify
from storage.forex import get_usd_to_inr_rate
from storage.shopify_auth import execute_shopify_graphql

# Load nell-fringe
target = None
for f in glob.glob(os.path.join(PROJECT_ROOT, "storage", "db", "jwpei", "products", "*.json")):
    with open(f, "r", encoding="utf-8") as fp:
        d = json.load(fp)
    if "nell-fringe" in d.get("handle", ""):
        target = d
        break

from storage.shopify_taxonomy import prepare_product_set_payload

payload = prepare_product_set_payload(target, 95.0)
for v in payload["variants"]:
    v["inventoryPolicy"] = "CONTINUE"
    v["inventoryItem"] = {"tracked": False}

from storage.shopify_sync import PRODUCT_SET_MUTATION

data, ext, err = execute_shopify_graphql(PRODUCT_SET_MUTATION, {"input": payload, "synchronous": True})
print("UserErrors:", data.get("productSet", {}).get("userErrors"))
print("Product:", data.get("productSet", {}).get("product", {}).get("id"))
