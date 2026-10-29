import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage.shopify_auth import execute_shopify_graphql

query = """
{
  products(first: 10, query: "vendor:COACH and (bag or tote or satchel or crossbody)") {
    edges {
      node {
        id
        title
        featuredImage {
          url
        }
      }
    }
  }
}
"""
data, _, err = execute_shopify_graphql(query)
print("Error:", err)
for edge in data.get("products", {}).get("edges", []):
    p = edge["node"]
    print(p["title"], "->", p["featuredImage"]["url"] if p.get("featuredImage") else None)
