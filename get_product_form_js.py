import os
import sys

PROJECT_ROOT = r"c:\workspace\dropship-scraper-portable-20260905\product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

THEME_ID = "gid://shopify/OnlineStoreTheme/198751387814"

q = """
{
  theme(id: "%s") {
    files(filenames: ["assets/product-form.js"]) {
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
""" % THEME_ID
data, ext, err = execute_shopify_graphql(q)
raw = data["theme"]["files"]["nodes"][0]["body"]["content"]
print(raw[:1500])
