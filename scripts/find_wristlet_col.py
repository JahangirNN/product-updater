#!/usr/bin/env python3
import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from storage.shopify_auth import execute_shopify_graphql

q = """
query {
  product(id: "gid://shopify/Product/15652532813990") {
    collections(first: 5) {
      nodes {
        id
        title
        handle
      }
    }
  }
}
"""
res, _, _ = execute_shopify_graphql(q)
print(res)
