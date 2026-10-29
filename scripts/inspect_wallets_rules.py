import os
import sys
import json
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query getColRules {
  col: collectionByHandle(handle: "wallets-accessories") {
    id
    title
    handle
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
"""

data, ext, err = execute_shopify_graphql(query)
print(json.dumps(data, indent=2))
