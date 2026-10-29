import os
import sys
import json
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql
from scripts.audit_luxury_bags_catalog import get_luxury_bag_products

catalog = get_luxury_bag_products()

def inspect_prod(prod_id, brand):
    q = """
    query getP($id: ID!) {
      product(id: $id) {
        id
        title
        handle
        status
        totalVariants
        options {
          id
          name
          values
        }
        variants(first: 3) {
          nodes {
            id
            title
            selectedOptions {
              name
              value
            }
            price
            sku
            image {
              url
            }
          }
        }
      }
    }
    """
    d, ext, err = execute_shopify_graphql(q, {"id": prod_id})
    p = d.get("product") if d else None
    print(f"=== {brand.upper()}: {prod_id} ===")
    if p:
        print(f"Title: {p.get('title')}")
        print(f"Total variants on Shopify: {p.get('totalVariants')}")
        print(f"Options on Shopify: {p.get('options')}")
        print("First 2 variants:")
        for v in (p.get("variants", {}).get("nodes", []))[:2]:
            print(f"  {v.get('title')} | {v.get('selectedOptions')} | img: {v.get('image')}")
    else:
        print(f"Error: {err}")

# Sample Coach
coach_prods = [p for p in catalog['coach'] if p.get('shopify_product_id')]
if coach_prods:
    inspect_prod(coach_prods[1]['shopify_product_id'], "coach")

# Sample JW PEI
jwpei_prods = [p for p in catalog['jwpei'] if p.get('shopify_product_id')]
if jwpei_prods:
    inspect_prod(jwpei_prods[1]['shopify_product_id'], "jwpei")

# Sample MK
mk_prods = [p for p in catalog['michaelkors'] if p.get('shopify_product_id')]
if mk_prods:
    inspect_prod(mk_prods[0]['shopify_product_id'], "michaelkors")
