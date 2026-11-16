import os
import sys
import json
import re

PROJECT_ROOT = r"c:\workspace\dropship-scraper-portable-20260905\product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

THEME_ID = "gid://shopify/OnlineStoreTheme/198751387814"

q = """
{
  theme(id: "%s") {
    files(filenames: ["templates/product.json"]) {
      nodes {
        body {
          ... on OnlineStoreThemeFileBodyText {
            content
          }
        }
      }
    }
  }
}
""" % THEME_ID
data, ext, err = execute_shopify_graphql(q)
raw = data["theme"]["files"]["nodes"][0]["body"]["content"]
if "/*" in raw:
    raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.DOTALL).strip()
pj = json.loads(raw)

pd_blocks = pj["sections"]["main"]["blocks"]["product-details"]["blocks"]
print("Product details block order:", pj["sections"]["main"]["blocks"]["product-details"]["block_order"])
for b_id, b_data in pd_blocks.items():
    print(f"Block: {b_id} -> type: {b_data.get('type')}, name: {b_data.get('name')}")
    if "blocks" in b_data:
        for sub_id, sub_data in b_data["blocks"].items():
            print(f"   Sub-block: {sub_id} -> type: {sub_data.get('type')}, name: {sub_data.get('name')}")
