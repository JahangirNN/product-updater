import os
import sys
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query {
  collections(first: 50) {
    nodes {
      id
      title
      handle
      productsCount {
        count
      }
      ruleSet {
        appliedDisjunctively
        rules {
          column
          relation
          condition
        }
      }
    }
  }
}
"""

data, ext, err = execute_shopify_graphql(query)
if err:
    print("Error:", err)
else:
    for c in data["collections"]["nodes"]:
        print(f"{c['handle']}: '{c['title']}' ({c['productsCount']['count']} products)")
