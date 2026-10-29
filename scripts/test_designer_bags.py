import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage.shopify_auth import execute_shopify_graphql

query = """
{
  collectionByHandle(handle: "designer-bags") {
    products(first: 10) {
      edges {
        node {
          title
          vendor
          productType
          featuredImage {
            url
          }
        }
      }
    }
  }
}
"""
data, _, err = execute_shopify_graphql(query)
for edge in data.get("collectionByHandle", {}).get("products", {}).get("edges", []):
    node = edge["node"]
    print(f"{node['title'][:40]:<40} | vendor: {node.get('vendor')} | img: {node['featuredImage']['url'] if node.get('featuredImage') else 'None'}")
