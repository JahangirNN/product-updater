import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage.shopify_auth import execute_shopify_graphql

query = """
query CheckCol($h: String!) {
  collectionByHandle(handle: $h) {
    id
    handle
    title
    image {
      url
      altText
    }
    products(first: 3) {
      nodes {
        id
        title
        featuredImage {
          url
        }
      }
    }
  }
}
"""
for h in ['premium-footwear', 'on-running', 'hoka', 'nike']:
    res, _, _ = execute_shopify_graphql(query, {'h': h})
    col = res.get('collectionByHandle') if res else None
    if col:
        print(h, "Image:", col.get('image'), "Products:", len(col.get('products', {}).get('nodes', [])))
    else:
        print(h, "NOT FOUND")
