import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage.shopify_auth import execute_shopify_graphql

collections_to_check = [
    "nike", "on-running", "hoka", "salomon", "tissot", "seiko", "citizen",
    "movado", "versace", "jw-pei", "michael-kors", "wallets-leather-goods",
    "womens-sunglasses", "mens-sunglasses", "totes", "crossbody-bags"
]

query = """
query GetColProducts($handle: String!) {
  collectionByHandle(handle: $handle) {
    id
    title
    products(first: 3) {
      edges {
        node {
          title
          featuredImage {
            url
          }
        }
      }
    }
  }
}
"""

for h in collections_to_check:
    data, _, err = execute_shopify_graphql(query, {"handle": h})
    col = data.get("collectionByHandle") if data else None
    if col and col.get("products", {}).get("edges"):
        edges = col["products"]["edges"]
        first_p = edges[0]["node"]
        img = first_p.get("featuredImage", {}).get("url") if first_p.get("featuredImage") else "No Image"
        print(f"[{h:<22}] -> {first_p['title'][:45]:<45} | {img}")
    else:
        print(f"[{h:<22}] -> No products found or error: {err}")
