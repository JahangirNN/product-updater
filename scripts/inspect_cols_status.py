import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage.shopify_auth import execute_shopify_graphql

query = """
query {
  collections(first: 20, query: "adidas OR asics OR nike OR footwear OR mens-shoes OR womens-shoes") {
    edges {
      node {
        id
        handle
        title
        productsCount { count }
        products(first: 3) {
          edges {
            node {
              id
              title
              vendor
              status
            }
          }
        }
      }
    }
  }
}
"""
res, _, err = execute_shopify_graphql(query)
if err:
    print("Error:", err)
else:
    for e in res.get("collections", {}).get("edges", []):
        n = e["node"]
        print(f"[{n['title']}] ({n['handle']}) | Count: {n.get('productsCount', {}).get('count')} | Published: {n.get('publishedOnCurrentPublication')}")
