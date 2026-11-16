import os
import sys

PROJECT_ROOT = r"c:\workspace\dropship-scraper-portable-20260905\product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query($cursor: String) {
  products(first: 100, after: $cursor) {
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      id
      title
      handle
      options {
        name
        values
      }
      variants(first: 20) {
        nodes {
          id
          title
          price
          compareAtPrice
          selectedOptions {
            name
            value
          }
        }
      }
    }
  }
}
"""

has_next = True
cursor = None
multi_variant_products = []
diff_price_products = []
total_count = 0

while has_next:
    data, ext, err = execute_shopify_graphql(query, variables={"cursor": cursor})
    if not data or "products" not in data:
        break
    p_data = data["products"]
    nodes = p_data["nodes"]
    total_count += len(nodes)
    for p in nodes:
        vars = p["variants"]["nodes"]
        if len(vars) > 1:
            multi_variant_products.append(p)
            prices = set(v["price"] for v in vars)
            if len(prices) > 1:
                diff_price_products.append(p)
    has_next = p_data["pageInfo"]["hasNextPage"]
    cursor = p_data["pageInfo"]["endCursor"]

print(f"Total products scanned: {total_count}")
print(f"Multi-variant products: {len(multi_variant_products)}")
print(f"Products with DIFFERENT variant prices: {len(diff_price_products)}")

for p in diff_price_products[:10]:
    print(f"\n{p['title']} (/products/{p['handle']}):")
    for v in p["variants"]["nodes"]:
        print(f"  - {v['title']}: {v['price']} (was {v['compareAtPrice']})")
