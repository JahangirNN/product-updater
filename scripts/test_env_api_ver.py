import os
import sys

PROJECT_ROOT = "product-updater"
sys.path.insert(0, PROJECT_ROOT)

os.environ["SHOPIFY_API_VERSION"] = "2024-07"

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

data, ext, err = execute_shopify_graphql(
    pub_mutation,
    variables={"query": "id:15993205981350"}
)
print("Data:", data)
print("Err:", err)
