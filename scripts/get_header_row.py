import sys
import os

PROJECT_ROOT = r"c:\workspace\dropship-scraper-portable-20260905\product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query getFiles($themeId: ID!, $filenames: [String!]!) {
  theme(id: $themeId) {
    files(filenames: $filenames) {
      nodes {
        filename
        body {
          ... on OnlineStoreThemeFileBodyText {
            content
          }
        }
      }
    }
  }
}
"""
data, ext, err = execute_shopify_graphql(query, {
    "themeId": "gid://shopify/OnlineStoreTheme/198751387814",
    "filenames": ["snippets/header-row.liquid"]
})
if data and "theme" in data and data["theme"]["files"]["nodes"]:
    print(data["theme"]["files"]["nodes"][0]["body"]["content"][:1500])
else:
    print("Not found or error:", err)
