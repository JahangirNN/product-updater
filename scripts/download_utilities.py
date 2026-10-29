import sys, os
sys.path.insert(0, r"c:\workspace\dropship-scraper-portable-20260905\product-updater")
from storage.shopify_auth import execute_shopify_graphql

query = """
query getFile($themeId: ID!, $filename: String!) {
  theme(id: $themeId) {
    files(filenames: [$filename]) {
      nodes {
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
data, resp, err = execute_shopify_graphql(query, variables={
    "themeId": "gid://shopify/OnlineStoreTheme/198751387814",
    "filename": "assets/utilities.js"
})
content = data["theme"]["files"]["nodes"][0]["body"]["content"]
with open("product-updater/horizon_clean_theme/assets/utilities.js", "w", encoding="utf-8") as f:
    f.write(content)
print(f"Downloaded assets/utilities.js ({len(content)} chars)")
