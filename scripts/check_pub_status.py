import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.shopify_auth import execute_shopify_graphql
import json
import glob

q = """
query getProduct($id: ID!) {
  product(id: $id) {
    id
    title
    handle
    status
    publishedAt
    onlineStoreUrl
    totalVariants
    featuredImage {
      url
    }
  }
}
"""

# Find a JW PEI product
jw_files = glob.glob("storage/db/jwpei/products/*.json")
for jwf in jw_files:
    with open(jwf, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("shopify_product_id"):
        res_jw, _, _ = execute_shopify_graphql(q, {"id": data["shopify_product_id"]})
        print("JW PEI PRODUCT:", json.dumps(res_jw, indent=2))
        break

# Find MK bags product
for mf in mk_files:
    with open(mf, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("product_type") != "Sunglasses" and data.get("shopify_product_id"):
        res_mk_bag, _, _ = execute_shopify_graphql(q, {"id": data["shopify_product_id"]})
        print("MK BAG:", json.dumps(res_mk_bag, indent=2))
        break

# Find MK eyewear product
mk_files = glob.glob("storage/db/michaelkors/products/*.json")
for mf in mk_files:
    with open(mf, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("product_type") == "Sunglasses" and data.get("shopify_product_id"):
        res_mk, _, _ = execute_shopify_graphql(q, {"id": data["shopify_product_id"]})
        print("MK SUNGLASSES:", json.dumps(res_mk, indent=2))
        break

q_intro = """
query {
  __type(name: "ProductSetInput") {
    inputFields {
      name
      type {
        name
        kind
        ofType {
          name
          kind
        }
      }
    }
  }
}
"""
res_intro, _, _ = execute_shopify_graphql(q_intro)
print("PRODUCT_SET_INPUT FIELDS:")
for f in res_intro.get("__type", {}).get("inputFields", []):
    print(f["name"])

