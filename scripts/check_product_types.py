import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query {
  products(first: 20, query: "Wallet") {
    edges {
      node {
        title
        vendor
        productType
        tags
      }
    }
  }
}
"""
data, ext, err = execute_shopify_graphql(query)
if data:
    for e in data['products']['edges']:
        n = e['node']
        print(f"Title: {n['title'][:40]} | Vendor: {n['vendor']} | Type: {n['productType']} | Tags: {[t for t in n['tags'] if not t.startswith('source_')]}")
else:
    print("Err:", err)
