import os
import sys
import json
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query IntrospectProductBulkPublish {
  __type(name: "ProductBulkPublishInput") {
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
print("ProductBulkPublishInput:", data, err)
