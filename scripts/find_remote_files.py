import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage.shopify_auth import execute_shopify_graphql

query = """
query getThemeFiles {
  theme(id: "gid://shopify/OnlineStoreTheme/198751387814") {
    files(first: 250) {
      nodes {
        filename
      }
    }
  }
}
"""
res = execute_shopify_graphql(query)
data = res[0]
nodes = data["data"]["theme"]["files"]["nodes"] if "data" in data else data["theme"]["files"]["nodes"]
for node in nodes:
    name = node["filename"].lower()
    if "cart" in name or "drawer" in name:
        print(node["filename"])
