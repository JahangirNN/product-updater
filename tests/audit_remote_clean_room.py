#!/usr/bin/env python3
"""
Remote Theme Clean-Room Auditor (ADR 0030)
Audits 100% of live theme files on gid://shopify/OnlineStoreTheme/198751387814
"""
import sys
import os
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

THEME_ID = "gid://shopify/OnlineStoreTheme/198751387814"
BANNED = [
    r'maestrooo',
    r'<loading-bar',
    r'<mega-menu-disclosure',
    r'<facet-link',
    r'<accordion-disclosure',
    r'support\.maestrooo\.com',
    r'theme\.js\b',
    r'theme\.css\b'
]

def run_remote_audit():
    q = """query getThemeFiles($id: ID!, $cursor: String) {
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
    }"""
    
    cursor = None
    total = 0
    violations = []
    
    while True:
        data, _, err = execute_shopify_graphql(q, {"id": THEME_ID, "cursor": cursor})
        if not data or "theme" not in data:
            print("GraphQL Error:", err)
            sys.exit(1)
            
        nodes = data["theme"]["files"]["nodes"]
        for n in nodes:
            total += 1
            fname = n["filename"]
            body = (n.get("body") or {}).get("content") or ""
            for pat in BANNED:
                if re.search(pat, body, re.I):
                    violations.append((fname, pat))
                    
        if not data["theme"]["files"]["pageInfo"]["hasNextPage"]:
            break
        cursor = data["theme"]["files"]["pageInfo"]["endCursor"]
        
    print(f"Total remote files scanned: {total}")
    print(f"Violations detected: {len(violations)}")
    if violations:
        for v in violations:
            print("  VIOLATION:", v)
        sys.exit(1)
    else:
        print("ALL REMOTE FILES CONFIRMED 100% CLEAN-ROOM COMPLIANT!")
        sys.exit(0)

if __name__ == "__main__":
    run_remote_audit()
