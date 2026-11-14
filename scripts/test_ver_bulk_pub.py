import sys
sys.path.insert(0, "product-updater")
from storage.shopify_auth import execute_shopify_graphql

pub_mutation = """
mutation bulkPub($query: String!) {
  productBulkPublish(
    search: $query,
    publicationIds: ["gid://shopify/Publication/328164671654"]
  ) {
    userErrors {
      field
      message
    }
  }
}
"""

for ver in ["2024-10", "2024-07", "2024-04", "2024-01"]:
    print(f"Testing api_version: {ver}...")
    data, ext, err = execute_shopify_graphql(
        pub_mutation,
        variables={"query": "id:15993205981350"},
        api_version=ver
    )
    if data:
        print(f"  SUCCESS on {ver}:", data)
        break
    else:
        print(f"  Failed on {ver}:", err)
