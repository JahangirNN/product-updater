import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query getAppInfo {
  currentAppInstallation {
    id
    accessScopes {
      handle
    }
    publication {
      id
      name
    }
  }
}
"""

data, ext, err = execute_shopify_graphql(query)
print("Data:", data)
print("Error:", err)
