import sys
sys.path.insert(0, "product-updater")
from storage.shopify_auth import execute_shopify_graphql

query = """
query GetProductPub($id: ID!) {
  product(id: $id) {
    id
    title
    publishedAt
    status
    onlineStoreUrl
  }
}
"""

GID = "gid://shopify/Product/15993205981350"
res, _, err = execute_shopify_graphql(query, variables={"id": GID})
print("Result:", res)
