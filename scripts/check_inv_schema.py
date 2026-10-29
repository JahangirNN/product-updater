import os
import sys
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query {
  invPolicy: __type(name: "ProductVariantInventoryPolicy") {
    enumValues {
      name
    }
  }
  invInput: __type(name: "InventoryItemInput") {
    inputFields {
      name
      type {
        name
        kind
      }
    }
  }
}
"""

data, ext, err = execute_shopify_graphql(query)
print(json.dumps(data, indent=2))
