import sys
import json
PROJECT_ROOT = "product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

def test_delete_failed_media():
    query = """
    {
      product(id: "gid://shopify/Product/15993205489830") {
        media(first: 20) {
          nodes {
            id
            status
          }
        }
      }
    }
    """
    data, _, err = execute_shopify_graphql(query)
    nodes = data.get("product", {}).get("media", {}).get("nodes", [])
    failed_ids = [m["id"] for m in nodes if m.get("status") == "FAILED"]
    print("Found failed media IDs:", failed_ids)
    if failed_ids:
        del_mutation = """
        mutation productDeleteMedia($productId: ID!, $mediaIds: [ID!]!) {
          productDeleteMedia(productId: $productId, mediaIds: $mediaIds) {
            deletedMediaIds
            userErrors {
              field
              message
            }
          }
        }
        """
        del_data, _, del_err = execute_shopify_graphql(
            del_mutation,
            variables={"productId": "gid://shopify/Product/15993205489830", "mediaIds": failed_ids}
        )
        print("Delete response:", del_data, del_err)

if __name__ == "__main__":
    test_delete_failed_media()
