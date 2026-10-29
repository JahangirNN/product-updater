import os
import sys
import glob
import json
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_sync import upsert_product_to_shopify
from storage.forex import get_usd_to_inr_rate
from storage.shopify_auth import execute_shopify_graphql

target = None
for f in glob.glob(os.path.join(PROJECT_ROOT, "storage", "db", "jwpei", "products", "*.json")):
    with open(f, "r", encoding="utf-8") as fp:
        d = json.load(fp)
    if "nell-fringe" in d.get("handle", ""):
        target = d
        break

if not target:
    print("Could not find nell-fringe")
    sys.exit(1)

print("Found target:", target.get("handle"))
pid = target["shopify_product_id"]

q = """
query getProd($id: ID!) {
  product(id: $id) {
    id
    variants(first: 10) {
      nodes {
        id
        title
        image { id url }
      }
    }
    media(first: 10) {
      nodes {
        ... on MediaImage {
          id
          image { url }
        }
      }
    }
  }
}
"""

data, _, _ = execute_shopify_graphql(q, {"id": pid})
print("\nBEFORE UPSERT variants in Shopify:")
for v in data["product"]["variants"]["nodes"]:
    print(" ", v["id"], v["title"], "image:", v["image"])
print("Total media in Shopify:", len(data["product"]["media"]["nodes"]))

rate = get_usd_to_inr_rate()
print("\nExecuting upsert_product_to_shopify...")
ok, p_node, err = upsert_product_to_shopify(target, rate)
print("Upsert result:", ok, "Error:", err)

# Check immediately after 1st upsert
data2, _, _ = execute_shopify_graphql(q, {"id": pid})
print("\nIMMEDIATELY AFTER 1st UPSERT variants in Shopify:")
for v in data2["product"]["variants"]["nodes"]:
    print(" ", v["id"], v["title"], "image:", v["image"])
print("Total media in Shopify:", len(data2["product"]["media"]["nodes"]))

# Wait 3 seconds and do a 2nd upsert to see if asynchronous ingestion resolves
print("\nWaiting 3 seconds for Shopify CDN ingestion...")
time.sleep(3)
ok2, p_node2, err2 = upsert_product_to_shopify(target, rate)
print("2nd Upsert result:", ok2, "Error:", err2)

data3, _, _ = execute_shopify_graphql(q, {"id": pid})
print("\nAFTER 2nd UPSERT variants in Shopify:")
for v in data3["product"]["variants"]["nodes"]:
    print(" ", v["id"], v["title"], "image:", v["image"])
