import os, sys
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
    "files": ["snippets/luxury_sidebar_navigation.liquid"]
})

if err:
    print("Err:", err)
else:
    node = data['theme']['files']['nodes'][0]
    content = node['body']['content']
    print(f"Remote length: {len(content)}")
    assert "/collections/womens-handbags/kate-spade" in content
    assert "/collections/wallets-accessories/kate-spade" in content
    assert "/collections/kate-spade" in content
    print("SUCCESS: Live theme snippets/luxury_sidebar_navigation.liquid contains all Kate Spade links!")
