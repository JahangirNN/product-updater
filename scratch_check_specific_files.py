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

files_to_check = [
    "sections/header.liquid",
    "snippets/header-sidebar.liquid",
    "snippets/luxury-sidebar-panels.liquid",
    "snippets/luxury_sidebar_navigation.liquid",
    "sections/header-group.json",
    "blocks/_header-menu.liquid"
]

data, ext, err = execute_shopify_graphql(query, {
    "themeId": "gid://shopify/OnlineStoreTheme/198751387814",
    "files": files_to_check
})
print("Result data:", data)
print("Result err:", err)
if data and 'theme' in data:
    for node in data['theme']['files']['nodes']:

        fn = node['filename']
        content = node['body']['content'] if node.get('body') else None
        print(f"=== {fn} (length: {len(content) if content else 0}) ===")
        if content:
            if "MAISON" in content:
                print("   CONTAINS 'MAISON'")
            if "Kate Spade" in content:
                print("   CONTAINS 'Kate Spade'")
            if "EXPLORE ALL HANDBAGS" in content:
                print("   CONTAINS 'EXPLORE ALL HANDBAGS'")
