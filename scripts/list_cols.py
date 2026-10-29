import sys, os, json
sys.path.insert(0, r"c:\Users\Administrator\WorkPlace\dropship-scraper-portable-20260905\product-updater")
from storage.shopify_auth import execute_shopify_graphql

query = """
{
  collections(first: 100) {
    edges {
      node {
        id
        title
        handle
        productsCount {
          count
        }
      }
    }
  }
}
"""

res, _, err = execute_shopify_graphql(query)
if res:
    for edge in res.get("collections", {}).get("edges", []):
        node = edge["node"]
        print(f"{node['handle']:30} | {node['title']:30} | {node['productsCount']['count']} prods | {node['id']}")
