import os
import sys

PROJECT_ROOT = r"c:\workspace\dropship-scraper-portable-20260905\product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

THEME_ID = "gid://shopify/OnlineStoreTheme/198751387814"

query = """
{
  theme(id: "%s") {
    name
    files(first: 250) {
      nodes {
        filename
      }
    }
  }
}
""" % THEME_ID

data, ext, err = execute_shopify_graphql(query)
if data and "theme" in data:
    files = [f["filename"] for f in data["theme"]["files"]["nodes"]]
    print(f"Theme Name: {data['theme']['name']}, Total Files: {len(files)}")
    for f in sorted(files):
        if "variant" in f or "price" in f or "product" in f or "main" in f or ".js" in f:
            print("  ", f)
else:
    print("Error:", err)
