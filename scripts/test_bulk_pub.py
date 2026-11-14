import sys
import os
import json
import time

PROJECT_ROOT = "product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

ONLINE_STORE_PUB_ID = "gid://shopify/Publication/328164671654"

BULK_PUB_MUTATION = """
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

query_str = "tag:Beauty"
res, _, err = execute_shopify_graphql(BULK_PUB_MUTATION, {"query": query_str})
print("Result:", res)
print("Err:", err)
