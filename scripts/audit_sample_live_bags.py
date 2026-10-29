import os
import sys
import glob
import json
import random

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

jw_files = glob.glob(os.path.join(PROJECT_ROOT, "storage", "db", "jwpei", "products", "*.json"))
coach_files = glob.glob(os.path.join(PROJECT_ROOT, "storage", "db", "coach", "products", "*.json"))

samples = []
for files, store in [(jw_files, "jwpei"), (coach_files, "coach")]:
    for f in files:
        with open(f, "r", encoding="utf-8") as fp:
            d = json.load(fp)
            if d.get("shopify_product_id") and len(d.get("variants") or []) >= 3:
                samples.append((store, d))

print(f"Total candidates with >= 3 variants: {len(samples)}")
random.seed(42)
chosen = random.sample(samples, 10)

query_template = """
query getProd($id: ID!) {
  product(id: $id) {
    id
    title
    handle
    variants(first: 20) {
      nodes {
        id
        title
        image {
          id
          url
        }
      }
    }
  }
}
"""

missing_total = 0
ok_total = 0

for store, prod in chosen:
    pid = prod["shopify_product_id"]
    data, ext, err = execute_shopify_graphql(query_template, variables={"id": pid})
    if err or not data:
        print(f"Error fetching {pid}: {err}")
        continue
    p = data.get("product")
    if not p:
        print(f"Product {pid} not found on Shopify!")
        continue
    variants = p.get("variants", {}).get("nodes", [])
    no_img = [v["title"] for v in variants if not v.get("image")]
    if no_img:
        missing_total += 1
        print(f"[{store.upper()}] {p['handle']:45} | Vars: {len(variants)} | Missing img: {len(no_img)} / {len(variants)}")
        print(f"    Missing sample: {no_img[:3]}")
    else:
        ok_total += 1
        print(f"[{store.upper()}] {p['handle']:45} | Vars: {len(variants)} | ALL HAVE IMAGES")

print("-" * 60)
print(f"Summary: {ok_total} products complete, {missing_total} products MISSING variant images!")
