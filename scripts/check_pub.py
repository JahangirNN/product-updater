import sys
sys.path.insert(0, "product-updater")
from storage.shopify_auth import execute_shopify_graphql

query = """
query GetPublications($id: ID!) {
  product(id: $id) {
    id
    title
    publishedAt
    resourcePublicationsV2(first: 10) {
      nodes {
        publication {
          id
          name
        }
        isPublished
      }
    }
  }
}
"""

GID = "gid://shopify/Product/15993205981350"
res, _, err = execute_shopify_graphql(query, variables={"id": GID})
p = res.get("product")
print("PublishedAt:", p.get("publishedAt"))
print("Publications:")
for pub in p.get("resourcePublicationsV2", {}).get("nodes", []):
    print(f"  - {pub['publication']['name']}: isPublished={pub['isPublished']}")
