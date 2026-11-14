import sys
import os
import json
import time

PROJECT_ROOT = "product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

ONLINE_STORE_PUB_ID = "gid://shopify/Publication/328164671654"

PUB_MUTATION = """
mutation publishablePublish($id: ID!, $input: [PublicationInput!]!) {
  publishablePublish(id: $id, input: $input) {
    userErrors {
      field
      message
    }
  }
}
"""

BULK_PUB_MUTATION = """
mutation bulkPub($query: String!) {
  productBulkPublish(
    search: $query,
    publicationIds: ["gid://shopify/Publication/328164671654"]
  ) {
    userErrors {
      field
      message
    }
  }
}
"""

PILOT_FILES = [
    "00746b4ef0f45103.json",
    "0263b15b38529dfe.json",
    "026b5e220a9f4985.json",
    "028a15e63b2cb6f9.json",
    "034159e1dcfe57b9.json",
    "04c4dd45f575ba41.json",
    "050a2d8ca25205a5.json",
    "05266852db888a70.json",
    "05824dadb0d3488f.json",
    "064cffc5d3a5b0a4.json",
    "0749eca097bf76c1.json",
    "08702e1da9320ab5.json",
    "09fb3e7f2425a515.json",
    "14f3a9acb4683314.json"
]

def publish_pilot():
    gids = []
    num_ids = []
    for fn in PILOT_FILES:
        fp = os.path.join(PROJECT_ROOT, "storage", "db", "sephora", "products", fn)
        with open(fp, "r", encoding="utf-8") as f:
            p = json.load(f)
            gid = p.get("shopify_product_id")
            if gid:
                gids.append(gid)
                num_ids.append(gid.split("/")[-1])

    print(f"Publishing {len(gids)} pilot products to Online Store ({ONLINE_STORE_PUB_ID})...")
    
    # 1. Publish each with publishablePublish
    for gid in gids:
        res, _, err = execute_shopify_graphql(PUB_MUTATION, {
            "id": gid,
            "input": [{"publicationId": ONLINE_STORE_PUB_ID}]
        })
        u_err = res.get("publishablePublish", {}).get("userErrors", []) if res else []
        if err or u_err:
            print(f"  Error publishing {gid}: {err or u_err}")
        else:
            print(f"  Published {gid}")

    # 2. Also run bulk publish query to ensure index update
    query_str = " OR ".join(f"id:{nid}" for nid in num_ids)
    res, _, err = execute_shopify_graphql(BULK_PUB_MUTATION, {"query": query_str})
    print("Bulk publish response:", res)

    print("\nWaiting 5 seconds for storefront indexing...")
    time.sleep(5)

if __name__ == "__main__":
    publish_pilot()
