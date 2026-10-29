import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query compareCols {
  women: collectionByHandle(handle: "womens-handbags") {
    id
    title
    handle
    updatedAt
  }
  men: collectionByHandle(handle: "mens-bags") {
    id
    title
    handle
    updatedAt
  }
}
"""

data, ext, err = execute_shopify_graphql(query)
print(data)
