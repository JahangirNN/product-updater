#!/usr/bin/env python3
"""
Investigate high value prices and potential corruption caused by `replace: ',00', ''`.
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

def check_catalog():
    query = """
    query getProducts($cursor: String) {
      products(first: 250, after: $cursor) {
        nodes {
          id
          title
          productType
          variants(first: 5) {
            nodes {
              id
              title
              price
              compareAtPrice
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    """
    cursor = None
    total_prods = 0
    high_value_variants = []
    round_hundreds = []

    while True:
        res, _, err = execute_shopify_graphql(query, {"cursor": cursor})
        if err or not res:
            break
        nodes = res.get("products", {}).get("nodes", [])
        total_prods += len(nodes)
        for p in nodes:
            for v in p["variants"]["nodes"]:
                price = float(v.get("price") or 0)
                cap = float(v.get("compareAtPrice") or 0)
                # Check if price has ,00 in formatted string
                # In standard comma formatting:
                # 100,000 -> has ",00"
                # 200,000 -> has ",00"
                # Any >= 100,000 has comma after hundreds or thousands
                # In Indian numbering: 1,00,000, 2,00,000
                if price >= 100000:
                    high_value_variants.append((p["title"], v["title"], price, cap))
                elif cap >= 100000:
                    high_value_variants.append((p["title"], v["title"], price, cap))
                
                # Also check any price that ends in 000, e.g., 50,000 or 10,000
                # In 10,000 -> Does "10,000" contain ",00"?
                # "10,000" contains ",00" as the first 3 characters after 10!
                # "10,000"[2:5] is ",00"!
                # If you do "10,000".replace(",00", ""), you get "10" + "0" = "100"!
                if str(int(price)).endswith("000"):
                    round_hundreds.append((p["title"], v["title"], price))

        if not res.get("products", {}).get("pageInfo", {}).get("hasNextPage"):
            break
        cursor = res["products"]["pageInfo"]["endCursor"]

    print(f"Total products scanned: {total_prods}")
    print(f"Variants >= 100,000: {len(high_value_variants)}")
    for item in high_value_variants[:10]:
        print(f"  High value: {item}")

    print(f"Variants with integer price ending in '000' (e.g. 10,000 or 50,000): {len(round_hundreds)}")
    for item in round_hundreds[:10]:
        print(f"  Round thousands: {item}")

if __name__ == "__main__":
    check_catalog()
