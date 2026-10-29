import os
import sys
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query getCol($handle: String!) {
  collectionByHandle(handle: $handle) {
    id
    title
    handle
    productsCount {
      count
    }
    ruleSet {
      appliedDisjunctively
      rules {
        column
        relation
        condition
      }
    }
    products(first: 10) {
      nodes {
        id
        title
        vendor
        productType
        tags
      }
    }
  }
}
"""

handles = ['women', 'womens', 'womens-boutique', 'womens-edit', 'womens-collection', 'womens-handbags', 'womens-watches', 'womens-sunglasses', 'men']
for h in handles:
    data, ext, err = execute_shopify_graphql(query, {'handle': h})
    col = data.get('collectionByHandle') if data else None
    if col:
        print(f"Collection: {h} | Title: {col.get('title')} | Count: {col.get('productsCount', {}).get('count')}")
        print(f"  Rules: {col.get('ruleSet')}")
        print(f"  First 3 products: {[p.get('title') for p in col.get('products', {}).get('nodes', [])[:3]]}")
    else:
        print(f"Collection: {h} -> NOT FOUND")
