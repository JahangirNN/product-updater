#!/usr/bin/env python3
import sys
import os
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql
import httpx

# Find products in catalog and their prices
q = """
query {
  products(first: 30) {
    nodes {
      id
      title
      handle
      variants(first: 1) {
        nodes {
          price
        }
      }
    }
  }
}
"""
res, _, _ = execute_shopify_graphql(q)
products = res["products"]["nodes"]
print(f"Total catalog products inspected: {len(products)}")

sample_7k = None
for p in products:
    price = p["variants"]["nodes"][0]["price"]
    print(f"  {p['handle']}: {price}")
    if float(price) % 1000 == 0:
        sample_7k = p

print("\nSample round-thousand product:", sample_7k)

# Now fetch the live storefront HTML for sample_7k (or home/collection)
if sample_7k:
    handle = sample_7k["handle"]
    url = f"https://therareavenue.com/products/{handle}"
    print(f"Fetching live URL: {url}...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        r = httpx.get(url, headers=headers, follow_redirects=True, timeout=15.0)
        print(f"Status code: {r.status_code}")
        if r.status_code == 200:
            html = r.text
            # Look for price in HTML
            prices_found = re.findall(r'Rs\.?\s*[\d,]+(?:\.\d+)?', html)
            print("Prices found in live HTML:", prices_found[:20])
    except Exception as e:
        print("HTTP error:", e)
