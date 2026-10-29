#!/usr/bin/env python3
"""
Empirical test of Jet Set Travel Wristlet (price 7000) on live storefront
"""
import os, sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

def get_product():
    q = """
    query {
      products(first: 1, query: "title:'Jet Set Travel Striped Signature Logo Convertible Wristlet'") {
        nodes {
          id
          title
          handle
          onlineStoreUrl
          variants(first: 1) {
            nodes {
              id
              price
              compareAtPrice
            }
          }
        }
      }
    }
    """
    res, _, _ = execute_shopify_graphql(q)
    print(res)

if __name__ == "__main__":
    get_product()
