import sys
sys.path.insert(0, "product-updater")
from storage.shopify_auth import execute_shopify_graphql

query = """
query GetProduct($id: ID!) {
  product(id: $id) {
    id
    title
    handle
    status
    tags
    vendor
    productType
    variants(first: 5) {
      nodes {
        id
        title
        price
        availableForSale
      }
    }
    collections(first: 5) {
      nodes {
        id
        title
        handle
      }
    }
  }
}
"""

GID = "gid://shopify/Product/15993205981350" # Saie Dew Blush
res, _, err = execute_shopify_graphql(query, variables={"id": GID})
p = res.get("product")
print("Title:", p.get("title"))
print("Handle:", p.get("handle"))
print("Status:", p.get("status"))
print("Tags:", p.get("tags"))
print("Collections:", [c["handle"] for c in p.get("collections", {}).get("nodes", [])])
print("Variants:", len(p.get("variants", {}).get("nodes", [])))
