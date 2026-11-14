import sys
sys.path.insert(0, "product-updater")
from storage.shopify_auth import execute_shopify_graphql

query = """
query GetScopes {
  app {
    installation {
      accessScopes {
        handle
      }
    }
  }
}
"""

res, _, err = execute_shopify_graphql(query)
print("Scopes result:", res)
if err:
    print("Err:", err)
