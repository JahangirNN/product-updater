import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from storage.shopify_auth import execute_shopify_graphql

ONLINE_STORE_PUB_ID = "gid://shopify/Publication/328164671654"

query = """
query GetColPub($h: String!) {
  collectionByHandle(handle: $h) {
    id
    title
    resourcePublications(first: 5) {
      nodes {
        publication {
          id
          name
        }
        isPublished
      }
    }
  }
}
"""
res, _, _ = execute_shopify_graphql(query, {"h": "nike"})
print("Nike collection publication:", res)

# Check first product in nike
query_prod = """
query GetProdPub {
  collectionByHandle(handle: "nike") {
    products(first: 3) {
      nodes {
        id
        title
        resourcePublications(first: 5) {
          nodes {
            publication {
              id
              name
            }
            isPublished
          }
        }
      }
    }
  }
}
"""
prod_res, _, _ = execute_shopify_graphql(query_prod)
print("Product publication:", prod_res)
