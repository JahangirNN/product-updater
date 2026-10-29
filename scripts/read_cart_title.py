import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage.shopify_auth import execute_shopify_graphql

query = """
query getThemeFile {
  theme(id: "gid://shopify/OnlineStoreTheme/198751387814") {
    files(filenames: ["blocks/_cart-title.liquid"]) {
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
node = data["data"]["theme"]["files"]["nodes"][0] if "data" in data else data["theme"]["files"]["nodes"][0]
print(node["body"]["content"])
