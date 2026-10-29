import os
import sys
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

pid = sys.argv[1] if len(sys.argv) > 1 else "gid://shopify/Product/15841761394854"

query = """
query getP($id: ID!) {
  product(id: $id) {
    id
    title
    handle
    totalVariants
    options {
      id
      name
      values
    }
    variants(first: 10) {
      nodes {
        id
        title
        selectedOptions {
          name
          value
        }
        image {
          id
          url
        }
      }
    }
    media(first: 15) {
      nodes {
        ... on MediaImage {
          id
          status
          image {
            id
            url
          }
        }
      }
    }
  }
}
"""

data, ext, err = execute_shopify_graphql(query, {"id": pid})
print("Result:")
print(json.dumps(data, indent=2))
if err:
    print("Error:", err)
