import os
import sys
import time
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from storage.shopify_auth import execute_shopify_graphql

ONLINE_STORE_PUB_ID = "gid://shopify/Publication/328164671654"

mutation = """
mutation publishCol($id: ID!, $input: [PublicationInput!]!) {
  publishablePublish(id: $id, input: $input) {
    userErrors {
      field
      message
    }
  }
}
"""

query_cols = """
query {
  collections(first: 100) {
    edges {
      node {
        id
        title
        handle
      }
    }
  }
}
"""

def publish_all_collections():
    data, _, err = execute_shopify_graphql(query_cols)
    if err or not data:
        print("Failed to fetch collections:", err)
        return

    cols = data.get("collections", {}).get("edges", [])
    print(f"Publishing {len(cols)} collections to Online Store publication...")

    for c in cols:
        node = c["node"]
        cid = node["id"]
        title = node["title"]
        handle = node["handle"]
        
        # Publish to Online Store
        res, _, perr = execute_shopify_graphql(mutation, {
            "id": cid,
            "input": [{"publicationId": ONLINE_STORE_PUB_ID}]
        })
        u_errs = res.get("publishablePublish", {}).get("userErrors", []) if res else []
        if u_errs or perr:
            print(f"  [{handle}] {title} -> Error: {u_errs or perr}")
        else:
            print(f"  [{handle}] {title} -> PUBLISHED")
        time.sleep(0.2)

if __name__ == "__main__":
    publish_all_collections()
