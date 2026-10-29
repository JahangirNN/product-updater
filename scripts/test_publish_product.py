import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql
from scripts.audit_luxury_bags_catalog import get_luxury_bag_products

catalog = get_luxury_bag_products()
coach_p = [p for p in catalog['coach'] if p.get('shopify_product_id')][0]
coach_id = coach_p['shopify_product_id']

# Test 1: productPublish mutation
mutation_1 = """
mutation publishProd($id: ID!) {
  publishablePublish(id: $id, input: {}) {
    publishable {
      availablePublicationCount
    }
    userErrors {
      field
      message
    }
  }
}
"""

data, ext, err = execute_shopify_graphql(mutation_1, {"id": coach_id})
print("publishablePublish result:", data, err)
