import sys, os, glob, json
sys.path.insert(0, r"c:\Users\Administrator\WorkPlace\dropship-scraper-portable-20260905\product-updater")
from storage.shopify_auth import execute_shopify_graphql

q = """
query getProd($id: ID!) {
  product(id: $id) {
    id
    title
    status
    handle
    vendor
    publishedAt
  }
}
"""

res, _, err = execute_shopify_graphql(q, {"id": "gid://shopify/Product/15850875748518"})
print("Result:", json.dumps(res, indent=2))
print("Error:", err)
