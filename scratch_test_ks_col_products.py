import sys
sys.path.insert(0, 'product-updater')
from storage.shopify_auth import execute_shopify_graphql

query = """
query getCollectionProducts {
  collectionByHandle(handle: "kate-spade") {
    id
    title
    image {
      url
    }
    productsCount {
      count
    }
  }
}
"""

data, ext, err = execute_shopify_graphql(query)
print(data)

