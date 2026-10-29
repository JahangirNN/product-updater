import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage.shopify_auth import execute_shopify_graphql
q = """
query {
  productByHandle(handle: "grenada-sunglasses") {
    id
    title
    tags
  }
}
"""
d, ext, err = execute_shopify_graphql(q)
print(d)
