import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
import json
from storage.shopify_auth import execute_shopify_graphql
from scripts.audit_luxury_bags_catalog import get_luxury_bag_products

catalog = get_luxury_bag_products()
query = """
query getProduct($id: ID!) {
  product(id: $id) {
    id
    title
    handle
    vendor
    productType
    descriptionHtml
    tags
    options {
      name
      values
    }
    variants(first: 10) {
      edges {
        node {
          id
          title
          sku
          price
          compareAtPrice
          selectedOptions {
            name
            value
          }
          image {
            url
          }
        }
      }
    }
  }
}
"""

for brand in ['coach', 'jwpei', 'michaelkors']:
    prods = catalog[brand]
    synced = [p for p in prods if p.get('shopify_product_id')]
    print(f"=== {brand.upper()}: {len(synced)}/{len(prods)} synced ===")
    if synced:
        # Check one multi-variant product if possible
        multi = [p for p in synced if len(p.get("variants", [])) > 1]
        sample = multi[0] if multi else synced[0]
        sp_id = sample['shopify_product_id']
        data, ext, err = execute_shopify_graphql(query, {'id': sp_id})
        if data and data.get('product'):
            p = data['product']
            print('Title:', p.get('title'))
            print('Vendor:', p.get('vendor'))
            print('ProductType:', p.get('productType'))
            print('Options:', p.get('options'))
            print('Variants count:', len(p.get('variants', {}).get('edges', [])))
            print('Description snippet:', (p.get('descriptionHtml') or '')[:300])
            for edge in p.get('variants', {}).get('edges', [])[:4]:
                print('  Var:', edge['node'])
        else:
            print('Error fetching:', err)
        print()
