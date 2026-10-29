import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage.shopify_auth import execute_shopify_graphql

query = """
{
  collectionByHandle(handle: "coach") {
    products(first: 25) {
      edges {
        node {
          title
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
    print(f"{node['title'][:50]:<50} | type: {node.get('productType')} | img: {node['featuredImage']['url'] if node.get('featuredImage') else 'None'}")
