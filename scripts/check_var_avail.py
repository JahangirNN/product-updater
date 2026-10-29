import os
import sys
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

q = """
query {
  product(id: "gid://shopify/Product/15841773813926") {
    status
    totalInventory
    variants(first: 5) {
      nodes {
        id
        title
        availableForSale
        inventoryQuantity
        inventoryPolicy
        inventoryItem {
          id
          tracked
        }
      }
    }
  }
}
"""
d, _, _ = execute_shopify_graphql(q)
print(json.dumps(d, indent=2))
