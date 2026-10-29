import sys, os
sys.path.insert(0, os.path.abspath('.'))
import json
from storage.shopify_auth import execute_shopify_graphql

query = """
query getProduct {
  productByHandle(handle: "versace-greca-sphere-quartz-silver-dial-ladies-watch-box-set-ve9c00324") {
    id
    title
    totalInventory
    variants(first: 5) {
      nodes {
        id
        title
        availableForSale
        price
      }
    }
  }
}
"""
data, resp, err = execute_shopify_graphql(query)
print("Product data:", data)
