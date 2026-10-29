import json
import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from storage.shopify_auth import execute_shopify_graphql

query = """
query {
  products(first: 5, query: "title:*Wesley*") {
    edges {
      node {
        id
        title
        handle
        vendor
        productType
        tags
      }
    }
  }
}
"""


data, ext, err = execute_shopify_graphql(query)
if err:
    print("Error:", err)
else:
    print(json.dumps(data, indent=2))
