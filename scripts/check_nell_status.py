import os
import sys
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query {
  product(id: "gid://shopify/Product/15841773813926") {
    id
    title
    variants(first: 10) {
      nodes {
        id
        title
        image {
          id
          url
        }
      }
    }
    media(first: 20) {
      nodes {
        ... on MediaImage {
          id
          status
          image {
            id
            url
            originalSrc
          }
        }
      }
    }
  }
}
"""

data, ext, err = execute_shopify_graphql(query)
print(json.dumps(data, indent=2))
