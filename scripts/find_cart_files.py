import sys, os
sys.path.insert(0, os.path.abspath('.'))
import json
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
data, resp, err = execute_shopify_graphql(query)
if not data:
    print('Failed:', err, resp)
    sys.exit(1)
files = [n['filename'] for n in data.get('theme', {}).get('files', {}).get('nodes', [])]
cart_files = [f for f in files if 'cart' in f.lower() or 'bubble' in f.lower()]
print('Cart/Bubble theme files:', cart_files)
