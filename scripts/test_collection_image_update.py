import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage.shopify_auth import execute_shopify_graphql

query = """
mutation UpdateCollectionImage($input: CollectionInput!) {
  collectionUpdate(input: $input) {
    collection {
      id
      handle
      image {
        url
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""

# Let's test on nike
# First get nike id
get_q = "{ collectionByHandle(handle: \"nike\") { id } }"
data, _, err = execute_shopify_graphql(get_q)
col_id = data["collectionByHandle"]["id"]
print("Nike Collection ID:", col_id)

variables = {
    "input": {
        "id": col_id,
        "image": {
            "src": "https://cdn.shopify.com/s/files/1/0759/1457/6038/files/IQ0292_060_P1.jpg?v=1791105407",
            "altText": "Nike Performance Footwear & Air Icons"
        }
    }
}
up_res, _, up_err = execute_shopify_graphql(query, variables)
print("Update Result:", up_res)
print("Update Error:", up_err)
