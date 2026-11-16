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
    try:
        return data["theme"]["files"]["nodes"][0]["body"]["content"]
    except Exception as e:
        return f"Error: {e}"

print("=== blocks/price.liquid ===")
p_price = get_file("blocks/price.liquid")
print(p_price[:1000])

print("\n=== snippets/price.liquid ===")
s_price = get_file("snippets/price.liquid")
print(s_price[:1000])

print("\n=== assets/product-price.js ===")
js_price = get_file("assets/product-price.js")
print(js_price[:1500])

print("\n=== assets/variant-picker.js ===")
js_var = get_file("assets/variant-picker.js")
print(js_var[:1500])
