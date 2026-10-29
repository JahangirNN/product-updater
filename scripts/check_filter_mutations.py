import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query {
  __schema {
    mutationType {
      fields {
        name
      }
    }
  }
}
"""
data, ext, err = execute_shopify_graphql(query)
if data:
    mutations = [f['name'] for f in data['__schema']['mutationType']['fields']]
    filter_mutations = [m for m in mutations if 'filter' in m.lower() or 'search' in m.lower()]
    print("Filter mutations:", filter_mutations)
else:
    print("Err:", err)
