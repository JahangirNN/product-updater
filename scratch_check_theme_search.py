import os, sys
sys.path.insert(0, 'product-updater')
from storage.shopify_auth import execute_shopify_graphql

query = """
query getThemeFiles($themeId: ID!) {
  theme(id: $themeId) {
    name
    role
    files(first: 250) {
      nodes {
        filename
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
"""

data, ext, err = execute_shopify_graphql(query, {"themeId": "gid://shopify/OnlineStoreTheme/198751387814"})
print("data:", data)
print("ext:", ext)
print("err:", err)

