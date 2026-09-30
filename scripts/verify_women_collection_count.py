import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query getCounts {
  women: collectionByHandle(handle: "women") {
    id
    handle
    title
    productsCount {
      count
    }
  }
  men: collectionByHandle(handle: "men") {
    id
    handle
    title
    productsCount {
      count
    }
  }
}
"""

data, ext, err = execute_shopify_graphql(query)
women_count = data.get("women", {}).get("productsCount", {}).get("count") if data else None
men_count = data.get("men", {}).get("productsCount", {}).get("count") if data else None

print(f"Collection 'women': {women_count} products")
print(f"Collection 'men': {men_count} products")
