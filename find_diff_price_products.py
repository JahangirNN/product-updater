import os
import sys

PROJECT_ROOT = r"c:\workspace\dropship-scraper-portable-20260905\product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
{
  products(first: 50) {
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

data, ext, err = execute_shopify_graphql(query)
products_with_diff_prices = []
all_multi_variant_products = []

for p in data["products"]["nodes"]:
    vars = p["variants"]["nodes"]
    if len(vars) > 1:
        prices = set(v["price"] for v in vars)
        all_multi_variant_products.append((p["handle"], p["title"], len(vars), prices))
        if len(prices) > 1:
            products_with_diff_prices.append((p["handle"], p["title"], [(v["title"], v["price"], v["compareAtPrice"]) for v in vars]))

print(f"Total multi-variant products found: {len(all_multi_variant_products)}")
print(f"Products with DIFFERENT prices across variants: {len(products_with_diff_prices)}")
for handle, title, var_prices in products_with_diff_prices:
    print(f"\nProduct: {title} (/products/{handle})")
    for v_title, v_price, v_compare in var_prices:
        print(f"  - {v_title}: Price = {v_price}, Compare = {v_compare}")

if not products_with_diff_prices:
    print("\nSample multi-variant products:")
    for handle, title, count, prices in all_multi_variant_products[:10]:
        print(f"  - {title} (/products/{handle}): {count} variants, prices: {prices}")
