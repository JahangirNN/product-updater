import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage.shopify_auth import execute_shopify_graphql

query = """
{
  collectionByHandle(handle: "nike") {
    id
    title
    products(first: 5) {
      nodes {
        id
        title
        status
        vendor
        featuredImage {
          url
        }
      }
    }
  }
}
"""
res, _, _ = execute_shopify_graphql(query)
print(res)
