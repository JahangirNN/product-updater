import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql
from scripts.audit_luxury_bags_catalog import get_luxury_bag_products

catalog = get_luxury_bag_products()
coach_p = [p for p in catalog['coach'] if p.get('shopify_product_id')][0]
coach_id = coach_p['shopify_product_id']

MUTATION = """
mutation testProductSet($input: ProductSetInput!) {
  productSet(input: $input, synchronous: true) {
    product {
      id
      title
      handle
      status
      publishedAt
      onlineStoreUrl
      options {
        name
        values
      }
      variants(first: 3) {
        nodes {
          id
          title
          sku
          price
          image {
            url
          }
        }
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""

first_var = coach_p['variants'][0]
img_url = first_var.get('image_url') or coach_p['images'][0]

payload = {
    "id": coach_id,
    "files": [
        {
            "originalSource": img_url,
            "contentType": "IMAGE"
        }
    ],
    "productOptions": [
        {
            "name": "Color",
            "values": [{"name": first_var.get("title")}]
        }
    ],
    "variants": [
        {
            "optionValues": [
                {
                    "optionName": "Color",
                    "name": first_var.get("title")
                }
            ],
            "price": "11414.00",
            "sku": "RARE-" + (first_var.get("sku") or "COACH-01"),
            "file": {
                "originalSource": img_url,
                "contentType": "IMAGE"
            }
        }
    ]
}

data, ext, err = execute_shopify_graphql(MUTATION, {"input": payload})
print("Upsert Data:", data)
print("Upsert Error:", err)

import time
time.sleep(3)

VERIFY_QUERY = """
query getVarImg($id: ID!) {
  product(id: $id) {
    id
    options {
      name
      values
    }
    variants(first: 3) {
      nodes {
        id
        title
        image {
          url
        }
      }
    }
  }
}
"""

v_data, ext, err = execute_shopify_graphql(VERIFY_QUERY, {"id": coach_id})
print("Verification Data:", v_data)
