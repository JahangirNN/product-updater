import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.shopify_auth import execute_shopify_graphql
from storage.shopify_collections import fetch_all_store_collections, COLLECTIONS_MANIFEST

def update_descriptions():
    existing = fetch_all_store_collections()
    manifest_by_handle = {c["handle"]: c for c in COLLECTIONS_MANIFEST}

    mutation = """
    mutation updateCollection($input: CollectionInput!) {
      collectionUpdate(input: $input) {
        collection {
          id
          handle
          title
          descriptionHtml
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    for handle in ["womens-watches", "mens-watches", "luxury-watches"]:
        if handle in existing and handle in manifest_by_handle:
            col_id = existing[handle]["id"]
            new_desc = manifest_by_handle[handle].get("descriptionHtml", "")
            print(f"Updating {handle} ({col_id}) with description: {new_desc}")
            data, ext, err = execute_shopify_graphql(mutation, variables={
                "input": {
                    "id": col_id,
                    "descriptionHtml": new_desc
                }
            })
            if err:
                print(f"Error updating {handle}: {err}")
            else:
                res = data.get("collectionUpdate", {})
                u_errors = res.get("userErrors", [])
                if u_errors:
                    print(f"UserErrors updating {handle}: {u_errors}")
                else:
                    print(f"Successfully updated {handle}!")

if __name__ == "__main__":
    update_descriptions()
