import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query {
  shop {
    productVendors(first: 50) {
      edges {
        node
      }
    }
  }
}
"""
data, ext, err = execute_shopify_graphql(query)
if data:
    vendors = [e['node'] for e in data['shop']['productVendors']['edges']]
    print("All store vendors:", vendors)
