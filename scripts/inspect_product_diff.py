import os
import sys
import json
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql
from scripts.audit_luxury_bags_catalog import get_luxury_bag_products

catalog = get_luxury_bag_products()
coach_id = [p for p in catalog['coach'] if p.get('shopify_product_id')][0]['shopify_product_id']
jwpei_id = [p for p in catalog['jwpei'] if p.get('shopify_product_id')][0]['shopify_product_id']

query = """
query getProds($coachId: ID!, $jwpeiId: ID!) {
  coach: product(id: $coachId) {
    id
    title
    handle
    status
    publishedAt
    onlineStoreUrl
    totalVariants
    variants(first: 5) {
      nodes {
        id
        title
        selectedOptions {
          name
          value
        }
        price
        sku
        barcode
        image {
          url
        }
      }
    }
  }
  jwpei: product(id: $jwpeiId) {
    id
    title
    handle
    status
    publishedAt
    onlineStoreUrl
    totalVariants
    variants(first: 5) {
      nodes {
        id
        title
        selectedOptions {
          name
          value
        }
        price
        sku
        barcode
        image {
          url
        }
      }
    }
  }
}
"""

data, ext, err = execute_shopify_graphql(query, {"coachId": coach_id, "jwpeiId": jwpei_id})
print("Result:")
print(json.dumps(data, indent=2))
