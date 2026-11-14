import sys
import os

PROJECT_ROOT = "product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

def main():
    query = """
    {
      collections(first: 100) {
        nodes {
          title
          handle
          productsCount {
            count
          }
        }
      }
    }
    """
    data, ext, err = execute_shopify_graphql(query)
    if err or not data:
        print("Error fetching collections:", err)
        return

    cols = data.get("collections", {}).get("nodes", [])
    print(f"Total collections returned: {len(cols)}")
    for c in cols:
        print(f"{c.get('title'):<35} {c.get('handle'):<30} {c.get('productsCount', {}).get('count', 0)}")

if __name__ == "__main__":
    main()
