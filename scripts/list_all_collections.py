import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
{
  collections(first: 100) {
    nodes {
      id
      title
      handle
      productsCount {
        count
      }
    }
  }
}
"""

data, resp, err = execute_shopify_graphql(query)
if err:
    print("Error:", err)
else:
    for c in data["collections"]["nodes"]:
        print(c["title"], "|", c["handle"], "|", c["productsCount"]["count"])
