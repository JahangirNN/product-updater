import sys
sys.path.insert(0, "product-updater")
from storage.shopify_auth import execute_shopify_graphql

query = """
mutation publishCol($id: ID!, $input: [PublicationInput!]!) {
  publishablePublish(id: $id, input: $input) {
    userErrors {
      field
      message
    }
  }
}
"""

res, _, err = execute_shopify_graphql(query, {
    "id": "gid://shopify/Collection/696312823974", # Beauty & Cosmetics collection
    "input": [{"publicationId": "gid://shopify/Publication/328164671654"}]
})
print("Result:", res)
print("Err:", err)
