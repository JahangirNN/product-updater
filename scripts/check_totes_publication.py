import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from storage.shopify_auth import execute_shopify_graphql

query = """
query checkPublishable {
  collection(id: "gid://shopify/Collection/693250687142") {
    id
    title
    handle
    resourcePublicationsV2(first: 5) {
      edges {
        node {
          publication {
            id
            name
          }
          isPublished
        }
      }
    }
  }
  publications(first: 10) {
    edges {
      node {
        id
        name
      }
    }
  }
}
"""

data, ext, err = execute_shopify_graphql(query)
print("Data:", data)
print("Error:", err)
