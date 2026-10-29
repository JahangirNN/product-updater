import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql
from storage.logger import log_info, log_success, log_error

query_get = """
{
  c1: collectionByHandle(handle: "ready-to-ship") {
    id
    title
    handle
  }
  c2: collectionByHandle(handle: "instant-ship") {
    id
    title
    handle
  }
}
"""

mutation_update = """
mutation updateCollection($input: CollectionInput!) {
  collectionUpdate(input: $input) {
    collection {
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
    userErrors {
      field
      message
    }
  }
}
"""

def update_collections():
    data, _, err = execute_shopify_graphql(query_get)
    if not data or err:
        log_error(f"Error fetching collections: {err}")
        return

    c1 = data.get("c1")
    c2 = data.get("c2")

    rule_set = {
        "appliedDisjunctively": True,
        "rules": [
            {"column": "TAG", "relation": "EQUALS", "condition": "Ready to Ship"},
            {"column": "TAG", "relation": "EQUALS", "condition": "instant-ship"},
            {"column": "TAG", "relation": "EQUALS", "condition": "manual-instant-ship-active"}
        ]
    }

    for col in [c1, c2]:
        if not col:
            continue
        cid = col["id"]
        inp = {
            "id": cid,
            "ruleSet": rule_set
        }
        res, _, m_err = execute_shopify_graphql(mutation_update, variables={"input": inp})
        if res and "collectionUpdate" in res:
            res_col = res["collectionUpdate"].get("collection")
            errs = res["collectionUpdate"].get("userErrors", [])
            if errs:
                log_error(f"Error updating collection {col['handle']}: {errs}")
            else:
                log_success(f"Updated collection '{res_col['title']}' ({res_col['handle']}) -> ProductsCount={res_col.get('productsCount', {}).get('count')}")
        else:
            log_error(f"GraphQL error updating {col['handle']}: {m_err}")

if __name__ == "__main__":
    update_collections()
