import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

query = """
query GetThemeFiles($themeId: ID!, $filenames: [String!]!) {
  theme(id: $themeId) {
    files(filenames: $filenames) {
      nodes {
        filename
        size
        updatedAt
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

THEME_ID = "gid://shopify/OnlineStoreTheme/198751387814"
files = [
    "snippets/luxury-desktop-nav.liquid",
    "snippets/luxury_sidebar_navigation.liquid",
    "snippets/product-card.liquid",
    "snippets/luxury-sidebar-panels.liquid",
    "snippets/header-sidebar.liquid"
]

res, _, err = execute_shopify_graphql(query, variables={"themeId": THEME_ID, "filenames": files})
if err:
    print(f"Error: {err}")
    sys.exit(1)

nodes = res.get("theme", {}).get("files", {}).get("nodes", [])
print(f"Found {len(nodes)} files on remote theme:")
for n in nodes:
    fn = n["filename"]
    content = n["body"]["content"] if n.get("body") else ""
    print(f"\n{fn}: size {len(content)}, updated {n.get('updatedAt')}")
    
    h_path = os.path.join(PROJECT_ROOT, "horizon_clean_theme", fn)
    t_path = os.path.join(PROJECT_ROOT, "theme", fn)
    
    h_match = open(h_path, encoding="utf-8").read() == content if os.path.exists(h_path) else False
    t_match = open(t_path, encoding="utf-8").read() == content if os.path.exists(t_path) else False
    print(f"  Matches horizon_clean_theme: {h_match}")
    print(f"  Matches theme: {t_match}")
    if os.path.exists(h_path):
        print(f"  horizon_clean_theme size: {os.path.getsize(h_path)}")
    if os.path.exists(t_path):
        print(f"  theme size: {os.path.getsize(t_path)}")
