import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from storage.shopify_auth import execute_shopify_graphql

query = """
query getSampleProducts {
  watches: products(first: 3, query: "status:ACTIVE vendor:Tissot") {
    nodes {
      handle
      title
      totalInventory
    }
  }
  coach: products(first: 3, query: "status:ACTIVE vendor:Coach") {
    nodes {
      handle
      title
      totalInventory
    }
  }
}
"""
res = execute_shopify_graphql(query)
print(json.dumps(res[0], indent=2))
