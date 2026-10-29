import sys, os, json, re
sys.path.insert(0, r"c:\workspace\dropship-scraper-portable-20260905\product-updater")
from storage.shopify_auth import execute_shopify_graphql

query = """
query getThemeFiles($themeId: ID!) {
  theme(id: $themeId) {
    files(filenames: ["templates/product.json"]) {
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
data_dict, extensions, error_msg = execute_shopify_graphql(query, {"themeId": "gid://shopify/OnlineStoreTheme/198751387814"})
nodes = (data_dict or {}).get("theme", {}).get("files", {}).get("nodes", [])
for node in nodes:
    content = node["body"]["content"]
    clean_json = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL).strip()
    data = json.loads(clean_json)
    prod_details = data.get("sections", {}).get("main", {}).get("blocks", {}).get("product-details", {})
    sub_blocks = prod_details.get("blocks", {})
    block_order = prod_details.get("block_order", [])
    print("Blocks inside product-details:")
    for b_id in block_order:
        print(f"  - {b_id}: {sub_blocks.get(b_id, {}).get('type')}")
