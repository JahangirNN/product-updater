import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query IntrospectProductUpdateInput {
  __type(name: "ProductUpdateInput") {
    inputFields {
      name
      type {
        name
        kind
      }
    }
  }
}
"""

data, ext, err = execute_shopify_graphql(query)
if data and data.get('__type'):
    for f in data['__type']['inputFields']:
        if any(k in f['name'].lower() for k in ['publish', 'status']):
            print(f['name'], '->', f['type'])
else:
    print("Error:", err)

from scripts.audit_luxury_bags_catalog import get_luxury_bag_products

catalog = get_luxury_bag_products()
coach_id = [p for p in catalog['coach'] if p.get('shopify_product_id')][0]['shopify_product_id']
jwpei_id = [p for p in catalog['jwpei'] if p.get('shopify_product_id')][0]['shopify_product_id']

data, ext, err = execute_shopify_graphql(query, {
    "coachId": coach_id,
    "jwpeiId": jwpei_id
})

print("Coach ID:", coach_id)
print("JW PEI ID:", jwpei_id)
print("Data:", data)
print("Error:", err)
