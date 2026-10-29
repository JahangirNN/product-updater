import os
import sys
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query getCollectionRules($handle: String!) {
  collectionByHandle(handle: $handle) {
    id
    title
    handle
    description
    ruleSet {
      appliedDisjunctively
      rules {
        column
        relation
        condition
      }
    }
    productsCount {
      count
    }
  }
}
"""

for h in ["luxury-watches", "wallets-accessories", "premium-footwear", "designer-bags", "footwear", "handbags"]:
    data, ext, err = execute_shopify_graphql(query, variables={"handle": h})
    col = data.get("collectionByHandle") if data else None
    if col:
        print(f"Handle: {col['handle']} | Title: {col['title']} | Count: {col.get('productsCount', {}).get('count')}")
        rs = col.get("ruleSet")
        if rs:
            print(f"  Rules (disjunctive={rs.get('appliedDisjunctively')}): {rs.get('rules')}")
        else:
            print("  Custom / Manual collection (no ruleSet)")
    else:
        print(f"Handle: {h} NOT FOUND")
