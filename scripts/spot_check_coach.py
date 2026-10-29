import sys
import os
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from storage.shopify_auth import execute_shopify_graphql

query = """
query getProds($ids: [ID!]!) {
  nodes(ids: $ids) {
    ... on Product {
      id
      title
      productType
      vendor
      onlineStoreUrl
      variants(first: 10) {
        edges {
          node {
            id
            title
            price
            compareAtPrice
            sku
          }
        }
      }
    }
  }
}
"""

spot_ids = [
    "gid://shopify/Product/15841760772262",  # Pouch In Signature Canvas (multi-variant $99 vs $119)
    "gid://shopify/Product/15841760805030",  # ID Wallet In Signature Canvas ($49)
    "gid://shopify/Product/15841760870566",  # Taylor Backpack In Signature Canvas ($269)
    "gid://shopify/Product/15848602402982",  # Brynn Sandal ($185)
    "gid://shopify/Product/15841770930342",  # Passport Card Case In Signature Canvas ($69)
]

res, ext, err = execute_shopify_graphql(query, {"ids": spot_ids})
if err:
    print(f"GraphQL Error: {err}")
    sys.exit(1)

for node in res.get("nodes", []):
    if not node:
        continue
    print("=" * 70)
    print(f"Product: {node['title']}")
    print(f"ID: {node['id']}")
    print(f"Vendor: {node['vendor']} | Category: {node['productType']}")
    print("Variants:")
    for edge in node.get("variants", {}).get("edges", []):
        v = edge["node"]
        price = v["price"]
        comp = v.get("compareAtPrice")
        cents = price.split(".")[0][-2:] if "." in price else price[-2:]
        charm_ok = (cents == "99")
        print(f"  - [{v['sku']}] {v['title']}: Price = ₹{price} (charm: {charm_ok}) | CompareAt = {comp}")
print("=" * 70)
