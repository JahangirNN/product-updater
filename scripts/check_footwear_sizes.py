import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
{
  collectionByHandle(handle: "beauty") {
    products(first: 5) {
      nodes {
        handle
        title
        vendor
        status
      }
    }
  }
}
"""

data, resp, err = execute_shopify_graphql(query)
if data:
    for p in data["collectionByHandle"]["products"]["nodes"]:
        print(p["status"], "|", p["vendor"], "|", p["handle"])
