import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.shopify_auth import execute_shopify_graphql

query = """
query getProduct($id: ID!) {
  product(id: $id) {
    id
    title
    handle
    status
    productType
    tags
    media(first: 10) {
      nodes {
        id
        status
        mediaContentType
        ... on MediaImage {
          image {
            url
            width
            height
          }
        }
      }
    }
    variants(first: 5) {
      nodes {
        id
        sku
        price
        compareAtPrice
      }
    }
    collections(first: 5) {
      nodes {
        id
        title
        handle
      }
    }
  }
}
"""

data, ext, err = execute_shopify_graphql(query, variables={"id": "gid://shopify/Product/15840666615974"})
print("ERR:", err)
print(json.dumps(data, indent=2))
