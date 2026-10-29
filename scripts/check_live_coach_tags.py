import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from storage.shopify_auth import execute_shopify_graphql

query = """
query getCoachTags {
  products(first: 5, query: "vendor:COACH") {
    edges {
      node {
        id
        title
        vendor
        tags
        updatedAt
      }
    }
  }
}
"""
data, ext, err = execute_shopify_graphql(query)
if data:
    for p in data['products']['edges']:
        print(p['node']['title'])
        print('  Updated:', p['node']['updatedAt'])
        print('  Tags:', p['node']['tags'])
else:
    print('Error:', err)
