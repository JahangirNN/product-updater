#!/usr/bin/env python3
"""
Exhaustive Audit of all 'money' filter usages across all remote theme files on:
Theme: gid://shopify/OnlineStoreTheme/198751387814
"""

import os
import sys
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

THEME_ID = "gid://shopify/OnlineStoreTheme/198751387814"

def audit_remote_money_filters():
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
    all_money_usages = []
    total_files = 0
    while True:
        data, _, err = execute_shopify_graphql(query, {"id": THEME_ID, "cursor": cursor})
        if err or not data:
            raise RuntimeError(f"GraphQL error: {err}")
        files_conn = data.get("theme", {}).get("files", {})
        for node in files_conn.get("nodes", []):
            total_files += 1
            fn = node.get("filename", "")
            body = node.get("body")
            content = body.get("content", "") if body else ""
            if "money" in content:
                for line_idx, line in enumerate(content.splitlines(), start=1):
                    if "money" in line:
                        all_money_usages.append((fn, line_idx, line.strip()))
        if not files_conn.get("pageInfo", {}).get("hasNextPage"):
            break
        cursor = files_conn["pageInfo"]["endCursor"]

    print(f"Scanned {total_files} files on theme {THEME_ID}.")
    print(f"Found {len(all_money_usages)} lines containing 'money'.")
    print("\n--- Summary by file ---")
    files_with_money = {}
    for fn, line_idx, line in all_money_usages:
        files_with_money.setdefault(fn, []).append((line_idx, line))

    for fn, lines in files_with_money.items():
        print(f"\nFile: {fn} ({len(lines)} occurrences)")
        for lnum, ltext in lines:
            has_strip = (".00" in ltext) or ("without_trailing" in ltext) or ("format-price" in ltext)
            status = "STRIPPED" if has_strip else "UNSTRIPPED / RAW"
            print(f"  L{lnum:4d} [{status}]: {ltext[:120]}")

if __name__ == "__main__":
    audit_remote_money_filters()
