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

print(get_file("templates/product.json"))
