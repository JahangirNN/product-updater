import os
import sys

PROJECT_ROOT = r"c:\workspace\dropship-scraper-portable-20260905\product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
{
  products(first: 10) {
    nodes {
      id
      title
      handle
      variants(first: 5) {
        nodes {
          id
          title
          price
        }
      }
    }
  }
}
"""

data, ext, err = execute_shopify_graphql(query)
print("Products query result:", data)
