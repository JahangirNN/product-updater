import os, sys, json
sys.path.insert(0, 'product-updater')
from storage.shopify_auth import execute_shopify_graphql

query = """
query getFiles($themeId: ID!, $files: [String!]!) {
  theme(id: $themeId) {
    files(filenames: $files) {
      nodes {
        filename
        body {
          ... on OnlineStoreThemeFileBodyText {
            content
          }
        }
      }
    }
  }
}
"""

data, ext, err = execute_shopify_graphql(query, {
    "themeId": "gid://shopify/OnlineStoreTheme/198751387814",
    "files": ["templates/index.json"]
})

if err:
    print("Err:", err)
else:
    node = data['theme']['files']['nodes'][0]
    print("Filename:", node['filename'])
    print("Body keys:", node.get('body'))


