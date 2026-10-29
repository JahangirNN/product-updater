import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query {
  __type(name: "QueryRoot") {
    fields {
      name
    }
  }
}
"""
data, ext, err = execute_shopify_graphql(query)
if data:
    fields = [f['name'] for f in data['__type']['fields']]
    filter_fields = [f for f in fields if 'filter' in f.lower() or 'search' in f.lower()]
    print("Filter/Search related fields:", filter_fields)
else:
    print("Err:", err)
