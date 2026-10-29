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

files = [
    'snippets/cart-products.liquid',
    'assets/product-form.js',
    'blocks/buy-buttons.liquid',
    'assets/component-cart-items.js'
]

os.makedirs('temp_remote_review', exist_ok=True)
for f in files:
    data, resp, err = execute_shopify_graphql(query, variables={
        "themeId": "gid://shopify/OnlineStoreTheme/198751387814",
        "filename": f
    })
    nodes = data.get('theme', {}).get('files', {}).get('nodes', [])
    if nodes and nodes[0].get('body'):
        content = nodes[0]['body']['content']
        out_path = os.path.join('temp_remote_review', f.replace('/', '_'))
        with open(out_path, 'w', encoding='utf-8') as out_f:
            out_f.write(content)
        print(f"Downloaded {f}: {len(content)} chars -> {out_path}")
    else:
        print(f"FAILED to download {f}")
