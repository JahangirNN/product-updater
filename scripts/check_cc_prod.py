import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from storage.shopify_auth import execute_shopify_graphql

query = """
query getCheckCheckProduct {
  product(id: "gid://shopify/Product/15886266794150") {
    id
    title
    handle
    status
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
        title
        price
        sku
        availableForSale
      }
    }
  }
}
"""

res = execute_shopify_graphql(query)
print(json.dumps(res, indent=2))
