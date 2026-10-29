import sys
import os
import json

sys.path.insert(0, r"C:\Users\Administrator\WorkPlace\dropship-scraper-portable-20260905\product-updater")
from storage.shopify_auth import execute_shopify_graphql
from storage.shopify_collections import provision_collection

# 1. Provision ready-to-ship
spec = {
    "title": "Ready to Ship",
    "handle": "ready-to-ship",
    "descriptionHtml": "<p>In-stock luxury designer pieces ready to ship immediately — authentic, verified, and delivered with express dispatch.</p>",
    "ruleSet": {
        "appliedDisjunctively": True,
        "rules": [
            {"column": "TAG", "relation": "EQUALS", "condition": "Ready to Ship"},
            {"column": "TAG", "relation": "EQUALS", "condition": "instant-ship"}
        ]
    }
}

print("Provisioning ready-to-ship collection...")
ok, node, status = provision_collection(spec)
print(f"Result: ok={ok}, status={status}, node={node}")

# 2. Update instant-ship collection to also match Ready to Ship tag
query_instant = """
query getInstantShip {
  collectionByHandle(handle: "instant-ship") {
    id
  }
}
"""
data, _, _ = execute_shopify_graphql(query_instant)
instant_id = data.get("collectionByHandle", {}).get("id") if data else None
if instant_id:
    mutation_update = """
    mutation updateCollection($input: CollectionInput!) {
      collectionUpdate(input: $input) {
        collection {
          id
          title
          handle
          ruleSet {
            appliedDisjunctively
            rules {
              column
              relation
              condition
            }
          }
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    up_payload = {
        "id": instant_id,
        "ruleSet": {
            "appliedDisjunctively": True,
            "rules": [
                {"column": "TAG", "relation": "EQUALS", "condition": "instant-ship"},
                {"column": "TAG", "relation": "EQUALS", "condition": "Ready to Ship"}
            ]
        }
    }
    data_up, _, err_up = execute_shopify_graphql(mutation_update, variables={"input": up_payload})
    print("instant-ship update result:", json.dumps(data_up, indent=2))
