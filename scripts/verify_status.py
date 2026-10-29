import sys
import os
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query checkCollections {
  rts: collectionByHandle(handle: "ready-to-ship") {
    title
    handle
    productsCount { count }
  }
  instant: collectionByHandle(handle: "instant-ship") {
    title
    handle
    productsCount { count }
  }
  mk: collectionByHandle(handle: "michael-kors") {
    title
    handle
    productsCount { count }
  }
}
"""

d, _, err = execute_shopify_graphql(query, allow_retry=False)
print("Collections status:", json.dumps(d, indent=2))
