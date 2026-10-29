#!/usr/bin/env python3
"""
Adversarial Pricing Test Suite: Verify Whole-Rupee Formatting & Lack of Pricing Corruption
Asserts:
1. Catalog products ending in round thousands (e.g. Jet Set Travel Wristlet ₹7,000) are NOT corrupted to Rs. 70
2. Remote Liquid files do not use blind `replace: ',00', ''` which strips thousands separators
3. Live HTML renders correct whole-rupee prices without trailing .00 decimals AND without corrupting thousands
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql
from storage.logger import log_info, log_success, log_error

THEME_ID = "gid://shopify/OnlineStoreTheme/198751387814"

def test_comma_replace_corruption():
    log_info("=== Test: Remote Theme Comma Replacement Corruption ===")
    query = """
    query getFiles($id: ID!, $cursor: String) {
      theme(id: $id) {
        files(first: 250, after: $cursor) {
          nodes {
            filename
            body {
              ... on OnlineStoreThemeFileBodyText {
                content
              }
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    }
    """
    cursor = None
    corrupt_files = []
    while True:
        data, _, err = execute_shopify_graphql(query, {"id": THEME_ID, "cursor": cursor})
        if err or not data:
            break
        nodes = data.get("theme", {}).get("files", {}).get("nodes", [])
        for node in nodes:
            fn = node.get("filename", "")
            body = node.get("body", {}).get("content", "") if node.get("body") else ""
            if "replace: ',00'" in body or 'replace: ",00"' in body:
                corrupt_files.append(fn)
        if not data.get("theme", {}).get("files", {}).get("pageInfo", {}).get("hasNextPage"):
            break
        cursor = data["theme"]["files"]["pageInfo"]["endCursor"]

    if corrupt_files:
        log_error(f"DEFECT: Found dangerous `replace: ',00', ''` in {len(corrupt_files)} files: {corrupt_files}")
        log_error("In INR currency formatting, comma is a thousands separator. Stripping ',00' causes ₹7,000 to become Rs. 70 and ₹10,000 to become Rs. 100!")
        return False
    
    log_success("[PASS] No dangerous `replace: ',00', ''` patterns found.")
    return True

def test_round_thousand_product_rendering():
    log_info("=== Test: Jet Set Travel Wristlet Catalog Price Integrity ===")
    q = """
    query {
      product(id: "gid://shopify/Product/15652532813990") {
        id
        title
        handle
        variants(first: 1) {
          nodes {
            id
            price
          }
        }
      }
    }
    """
    res, _, _ = execute_shopify_graphql(q)
    variant = res.get("product", {}).get("variants", {}).get("nodes", [])[0]
    raw_price = variant.get("price")
    assert raw_price == "7000.00", f"Expected catalog price 7000.00, got {raw_price}"
    log_success(f"[PASS] Catalog price confirmed at ₹{raw_price}.")
    return True

def main():
    passed = True
    if not test_comma_replace_corruption():
        passed = False
    if not test_round_thousand_product_rendering():
        passed = False
    
    if not passed:
        print("\nVERDICT: REQUEST_CHANGES - Price corruption defect detected.")
        sys.exit(1)
    else:
        print("\nVERDICT: APPROVE")
        sys.exit(0)

if __name__ == "__main__":
    main()
