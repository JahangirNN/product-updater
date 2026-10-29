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
data, resp, err = execute_shopify_graphql(query, variables={
    "themeId": "gid://shopify/OnlineStoreTheme/198751387814",
    "filename": "assets/cart-icon.js"
})
nodes = data.get('theme', {}).get('files', {}).get('nodes', [])
content = nodes[0]['body']['content']
os.makedirs('horizon_clean_theme/assets', exist_ok=True)
with open('horizon_clean_theme/assets/cart-icon.js', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)
print('Saved original assets/cart-icon.js, size:', len(content))
