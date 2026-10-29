import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage.shopify_auth import execute_shopify_graphql
import json

query = """
query {
  collections(first: 50, query: "men OR footwear OR shoes") {
    edges {
      node {
        id
        handle
        title
        productsCount { count }
        ruleSet {
          appliedDisjunctively
          rules {
            column
            relation
            condition
          }
        }
      }
    }
  }
}
"""
res, _, err = execute_shopify_graphql(query)
if err or not res:
    print("Error:", err)
else:
    for c in res["collections"]["edges"]:
        node = c["node"]
        print(f"[{node['title']}] ({node['handle']}) | Count: {node.get('productsCount', {}).get('count')} | Rules: {node.get('ruleSet')}")
