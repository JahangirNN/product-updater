import sys
sys.path.insert(0, "product-updater")
from storage.shopify_auth import execute_shopify_graphql

query = """
query GetSampleProds {
  products(first: 5, query: "status:active") {
    nodes {
      id
      title
      handle
      publishedAt
      status
      onlineStoreUrl
      collections(first: 5) {
        nodes {
          handle
        }
      }
    }
  }
}
"""

res, _, err = execute_shopify_graphql(query)
for p in res.get("products", {}).get("nodes", []):
    print(p)
