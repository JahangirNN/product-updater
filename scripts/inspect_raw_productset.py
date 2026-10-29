import os
import sys
import glob
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_taxonomy import prepare_product_set_payload
from storage.shopify_auth import execute_shopify_graphql

target = None
for f in glob.glob(os.path.join(PROJECT_ROOT, "storage", "db", "jwpei", "products", "*.json")):
    with open(f, "r", encoding="utf-8") as fp:
        d = json.load(fp)
    if "nell-fringe" in d.get("handle", ""):
        target = d
        break

payload = prepare_product_set_payload(target, 95.0)

MUTATION = """
mutation productSet($input: ProductSetInput!, $synchronous: Boolean!) {
  productSet(input: $input, synchronous: $synchronous) {
    product {
      id
      title
      handle
      variants(first: 10) {
        nodes {
          id
          title
          image {
            id
            url
          }
        }
      }
      media(first: 10) {
        nodes {
          ... on MediaImage {
            id
            image {
              url
              originalSrc
            }
          }
        }
      }
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

data, ext, err = execute_shopify_graphql(MUTATION, {"input": payload, "synchronous": True})
print("DATA:")
print(json.dumps(data, indent=2))
print("ERR:", err)
