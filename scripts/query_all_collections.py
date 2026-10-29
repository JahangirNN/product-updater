import os
import sys
import json
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query getCollections {
  collections(first: 100) {
    edges {
      node {
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
      }
    }
  }
}
"""

data, ext, err = execute_shopify_graphql(query)
if data:
    cols = data['collections']['edges']
    print(f"Total collections found: {len(cols)}")
    for c in cols:
        node = c['node']
        pcount = node.get('productsCount', {}).get('count')
        print(f"Handle: {node['handle']:35} | Title: {node['title']:30} | Products: {pcount}")
else:
    print("Error:", err)
