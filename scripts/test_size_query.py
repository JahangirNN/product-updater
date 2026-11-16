import os
import sys
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

test_queries = [
    "UK 8",
    "variants.title:UK 8",
    "tag:footwear AND 'UK 8'",
    "footwear AND 'UK 8'",
]

for tq in test_queries:
    query = """
    {
      products(first: 3, query: "%s") {
        nodes {
          id
          title
          options {
            name
            values
          }
        }
      }
    }
    """ % tq
    data, resp, err = execute_shopify_graphql(query)
    count = len(data.get("products", {}).get("nodes", [])) if data else 0
    print(f"Query: {tq:<30} -> Found {count} products")
