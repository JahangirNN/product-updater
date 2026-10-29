import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage.shopify_auth import execute_shopify_graphql

query = """
{
  collectionByHandle(handle: "coach") {
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
data, _, err = execute_shopify_graphql(query)
print("Data:", data)
print("Error:", err)
