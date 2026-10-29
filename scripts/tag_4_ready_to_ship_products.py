import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql
from storage.logger import log_info, log_success, log_error

PRODUCT_IDS = [
    "gid://shopify/Product/15652523770022",
    "gid://shopify/Product/15652529143974",
    "gid://shopify/Product/15652532813990",
    "gid://shopify/Product/15652511547558",
]

TAGS_TO_ADD = [
    "Ready to Ship",
    "instant-ship",
    "manual-instant-ship-active"
]

MUTATION_TAGS_ADD = """
mutation tagsAdd($id: ID!, $tags: [String!]!) {
  tagsAdd(id: $id, tags: $tags) {
    node {
      id
      ... on Product {
        title
        tags
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""

def tag_products():
    print("=" * 80)
    print("ADDING 'Ready to Ship' TAGS TO THE 4 PRODUCTS")
    print("=" * 80)

    for pid in PRODUCT_IDS:
        data, _, err = execute_shopify_graphql(MUTATION_TAGS_ADD, variables={"id": pid, "tags": TAGS_TO_ADD})
        if err:
            log_error(f"Error tagging {pid}: {err}")
            continue
        res = data.get("tagsAdd", {})
        errs = res.get("userErrors", [])
        if errs:
            log_error(f"UserErrors on {pid}: {errs}")
        else:
            node = res.get("node", {})
            log_success(f"Successfully tagged: '{node.get('title')}' -> Ready tags added!")

if __name__ == "__main__":
    tag_products()
