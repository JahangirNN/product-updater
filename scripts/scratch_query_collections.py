import os
import sys
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
{
  collections(first: 50) {
    nodes {
      id
      title
      handle
      productsCount {
        count
      }
    }
  }
}
"""

data, ext, err = execute_shopify_graphql(query)
if data:
    for node in data.get("collections", {}).get("nodes", []):
        t = node["title"]
        h = node["handle"]
        cnt = node.get("productsCount", {}).get("count")
        print(f"{h:35} | {cnt:5} products | {t}")
else:
    print("Error:", err)
