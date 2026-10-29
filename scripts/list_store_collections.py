import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage.shopify_auth import execute_shopify_graphql

query = """
{
  collections(first: 100) {
    edges {
      node {
        id
        handle
        title
        productsCount {
          count
        }
        image {
          url
        }
      }
    }
  }
}
"""
data, ext, err = execute_shopify_graphql(query)
if err:
    print(f"Error: {err}")
    sys.exit(1)

collections = data.get("collections", {}).get("edges", [])
print(f"Total Collections: {len(collections)}")
for edge in collections:
    node = edge["node"]
    handle = node["handle"]
    cnt = node.get("productsCount", {}).get("count", 0)
    img = bool(node.get("image"))
    title = node["title"]
    print(f"{handle:<32} | count: {cnt:<5} | img: {str(img):<5} | title: {title}")
