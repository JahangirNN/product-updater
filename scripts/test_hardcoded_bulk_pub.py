import sys
sys.path.insert(0, "product-updater")
from storage.shopify_auth import execute_shopify_graphql

pub_mutation = """
mutation {
  productBulkPublish(
    search: "id:15993205981350",
    publicationIds: ["gid://shopify/Publication/328164671654"]
  ) {
    userErrors {
      field
      message
    }
  }
}
"""
data, ext, err = execute_shopify_graphql(pub_mutation)
print("Data:", data)
print("Err:", err)
