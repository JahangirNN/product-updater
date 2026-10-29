import sys, os
sys.path.insert(0, os.path.abspath('.'))
import json
from storage.shopify_auth import execute_shopify_graphql

query = """
query getFile($themeId: ID!, $filename: String!) {
  theme(id: $themeId) {
    files(filenames: [$filename]) {
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
for fname in ['snippets/cart-bubble.liquid']:
    data, resp, err = execute_shopify_graphql(query, variables={
        "themeId": "gid://shopify/OnlineStoreTheme/198751387814",
        "filename": fname
    })
    nodes = data.get('theme', {}).get('files', {}).get('nodes', [])
    if nodes and nodes[0].get('body'):
        print(f"=== {fname} ===")
        print(nodes[0]['body'].get('content'))
    else:
        print(f"=== {fname} NOT FOUND ===")
