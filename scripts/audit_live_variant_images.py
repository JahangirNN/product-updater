import os
import sys
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query getBags {
  products(first: 100) {
    nodes {
      id
      title
      handle
      vendor
      productType
      totalVariants
      variants(first: 20) {
        nodes {
          id
          title
          image {
            id
            url
          }
        }
      }
    }
  }
}
"""

data, ext, err = execute_shopify_graphql(query)
if err:
    print("GraphQL Error:", err)
    sys.exit(1)

products = data.get("products", {}).get("nodes", [])

print(f"Total products fetched: {len(products)}")
for p in products[:15]:
    print(f"Product: {p['handle']} | Type: {p.get('productType')} | Vendor: {p.get('vendor')} | TotalVariants: {p.get('totalVariants')} | VariantsFetched: {len(p.get('variants', {}).get('nodes', []))}")

