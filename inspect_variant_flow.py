import os
import sys

PROJECT_ROOT = r"c:\workspace\dropship-scraper-portable-20260905\product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

THEME_ID = "gid://shopify/OnlineStoreTheme/198751387814"

def get_file(fn):
    q = """
    {
      theme(id: "%s") {
        files(filenames: ["%s"]) {
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
    """ % (THEME_ID, fn)
    data, ext, err = execute_shopify_graphql(q)
    return data["theme"]["files"]["nodes"][0]["body"]["content"]

print("=== assets/product-price.js FULL ===")
print(get_file("assets/product-price.js"))

print("\n=== assets/variant-picker.js (methods) ===")
vp = get_file("assets/variant-picker.js")
for line in vp.split("\n"):
    if "async " in line or "handle" in line or "dispatch" in line or "render" in line or "update" in line or "fetch" in line:
        print("  ", line[:100])
