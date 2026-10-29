import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage.shopify_auth import execute_shopify_graphql

query = """
query getThemeFile {
  theme(id: "gid://shopify/OnlineStoreTheme/198751387814") {
    files(filenames: ["snippets/cart-products.liquid"]) {
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
res = execute_shopify_graphql(query)
data = res[0]
if "data" in data:
    node = data["data"]["theme"]["files"]["nodes"][0]
else:
    node = data["theme"]["files"]["nodes"][0]
content = node["body"]["content"]
print("Fetched content length:", len(content), "lines:", len(content.splitlines()))

# Save clean copy locally with Unix LF
out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "horizon_clean_theme", "snippets", "cart-products.liquid")
with open(out_path, "w", encoding="utf-8", newline="\n") as f:
    f.write(content.replace("\r", ""))
print("Saved clean file to", out_path)
