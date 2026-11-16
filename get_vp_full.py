import os
import sys

PROJECT_ROOT = r"c:\workspace\dropship-scraper-portable-20260905\product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

THEME_ID = "gid://shopify/OnlineStoreTheme/198751387814"

q = """
{
  theme(id: "%s") {
    files(filenames: ["assets/variant-picker.js"]) {
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
with open("variant_picker_full.js", "w", encoding="utf-8") as f:
    f.write(raw)
print("Saved variant_picker_full.js, size:", len(raw))
