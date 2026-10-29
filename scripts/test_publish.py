import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from storage.shopify_auth import execute_shopify_graphql

query = """
mutation publishCol($id: ID!) {
  publishablePublish(id: $id, input: {}) {
    userErrors {
      field
      message
    }
  }
}
"""

data, ext, err = execute_shopify_graphql(query, {"id": "gid://shopify/Collection/693250687142"})
print("Data:", data)
print("Error:", err)
