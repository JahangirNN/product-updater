import os
import sys
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
{
  products(first: 10, query: "tag:footwear OR product_type:shoes OR product_type:sneakers OR footwear OR shoes") {
    nodes {
      id
      title
      handle
      productType
      tags
      options {
        name
        values
      }
      variants(first: 15) {
        nodes {
          title
          selectedOptions {
            name
            value
          }
        }
      }
    }
  }
  collections(first: 20) {
    nodes {
      id
      title
      handle
      productsCount {
        count
      }
    }
  }
}
"""

data, resp, err = execute_shopify_graphql(query)
if err:
    print("Error:", err)
else:
    print(json.dumps(data, indent=2))
