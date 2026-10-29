#!/usr/bin/env python3
import os, sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

THEME_ID = "gid://shopify/OnlineStoreTheme/198751387814"

def find_comma_replace_files():
    query = """
    query getFiles($id: ID!, $cursor: String) {
      theme(id: $id) {
        files(first: 250, after: $cursor) {
          nodes {
            filename
            body {
              ... on OnlineStoreThemeFileBodyText {
                content
              }
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    }
    """
    cursor = None
    files_with_comma_00 = []
    total_files = 0
    while True:
        data, _, err = execute_shopify_graphql(query, {"id": THEME_ID, "cursor": cursor})
        if err or not data:
            break
        nodes = data.get("theme", {}).get("files", {}).get("nodes", [])
        total_files += len(nodes)
        for node in nodes:
            fn = node.get("filename", "")
            body = node.get("body")
            content = body.get("content", "") if body else ""
            if "replace: ',00'" in content or 'replace: ",00"' in content:
                # Count occurrences
                count = content.count("replace: ',00'") + content.count('replace: ",00"')
                files_with_comma_00.append((fn, count))
        if not data.get("theme", {}).get("files", {}).get("pageInfo", {}).get("hasNextPage"):
            break
        cursor = data["theme"]["files"]["pageInfo"]["endCursor"]

    print(f"Total files scanned: {total_files}")
    print(f"Files with replace: ',00': {len(files_with_comma_00)}")
    for fn, count in files_with_comma_00:
        print(f"  • {fn}: {count} occurrences")

if __name__ == "__main__":
    find_comma_replace_files()
