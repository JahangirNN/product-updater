import json
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query getCollections($cursor: String) {
  collections(first: 100, after: $cursor) {
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        id
        title
        handle
        productsCount {
          count
        }
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

def fetch_all():
    cursor = None
    all_cols = []
    while True:
        res, _, err = execute_shopify_graphql(query, {"cursor": cursor})
        if err:
            print("GraphQL Error:", err)
            break
        data = res.get("collections", {})
        edges = data.get("edges", [])
        all_cols.extend([e["node"] for e in edges])
        if not data.get("pageInfo", {}).get("hasNextPage"):
            break
        cursor = data.get("pageInfo", {}).get("endCursor")

    print(f"Total collections found: {len(all_cols)}\n")
    for node in sorted(all_cols, key=lambda x: x["title"].lower()):
        rules = []
        if node.get("ruleSet"):
            rules = [f"{r['column']} {r['relation']} '{r['condition']}'" for r in node["ruleSet"].get("rules", [])]
            rule_str = (" OR " if node["ruleSet"].get("appliedDisjunctively") else " AND ").join(rules)
        else:
            rule_str = "MANUAL / CUSTOM COLLECTION"
        cnt = (node.get("productsCount") or {}).get("count", 0)
        print(f"[{node['title']}] | handle: {node['handle']} | count: {cnt}")
        print(f"  Rules: {rule_str}")

if __name__ == "__main__":
    fetch_all()
