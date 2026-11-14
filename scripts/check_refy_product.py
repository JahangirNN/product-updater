import sys
import json
PROJECT_ROOT = "product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

def main():
    query = """
    {
      product(id: "gid://shopify/Product/15994600816806") {
        id
        title
        handle
        status
        featuredImage {
          url
        }
        media(first: 10) {
          nodes {
            id
            mediaContentType
            status
            ... on MediaImage {
              image {
                url
              }
            }
          }
        }
      }
    }
    """
    data, ext, err = execute_shopify_graphql(query)
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    main()
