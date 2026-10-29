import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage.shopify_auth import execute_shopify_graphql

query = """
{
  files(first: 50) {
    edges {
      node {
        ... on MediaImage {
          id
          image {
            url
            originalSrc
          }
          alt
        }
      }
    }
  }
}
"""
data, ext, err = execute_shopify_graphql(query)
if err:
    print(f"Error: {err}")
    sys.exit(1)

files = data.get("files", {}).get("edges", [])
print(f"Total Files in store: {len(files)}")
for edge in files:
    node = edge.get("node", {})
    img = node.get("image", {})
    print(f"{node.get('id')} | alt: {node.get('alt')} | url: {img.get('url')}")
