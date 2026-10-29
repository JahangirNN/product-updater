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
for fname in ["snippets/luxury-desktop-nav.liquid"]:
    data, resp, err = execute_shopify_graphql(query, variables={
        "themeId": "gid://shopify/OnlineStoreTheme/198751387814",
        "filename": fname
    })
    c = data["theme"]["files"]["nodes"][0]["body"]["content"]
    for line in c.split("\n"):
        if "hover" in line or "luxury-mega-menu" in line:
            print(line[:100])
