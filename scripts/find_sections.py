import sys
import os

PROJECT_ROOT = r"c:\workspace\dropship-scraper-portable-20260905\product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query getFiles($themeId: ID!) {
  theme(id: $themeId) {
    files(first: 250) {
      nodes {
        filename
      }
    }
  }
}
"""
data, ext, err = execute_shopify_graphql(query, {
    "themeId": "gid://shopify/OnlineStoreTheme/198751387814"
})
if data and "theme" in data:
    for n in sorted([x['filename'] for x in data["theme"]["files"]["nodes"]]):
        if n.startswith("sections/") or "header" in n:
            print(n)
