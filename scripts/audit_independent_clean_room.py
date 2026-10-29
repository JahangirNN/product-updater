#!/usr/bin/env python3
"""
Auditor Independent Clean-Room & Anti-Copyright Verification Script
Directly inspects remote Shopify Theme gid://shopify/OnlineStoreTheme/198751387814
and local horizon_clean_theme directory for all prohibited tokens:
1. maestrooo
2. <loading-bar
3. <mega-menu-disclosure
4. <facet-link
5. <accordion-disclosure
6. support.maestrooo.com
7. theme.js
"""
import sys
import re
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

THEME_ID = "gid://shopify/OnlineStoreTheme/198751387814"

BANNED_TOKENS = [
    ("maestrooo", re.compile(r"maestrooo", re.IGNORECASE)),
    ("<loading-bar", re.compile(r"<\s*loading-bar\b", re.IGNORECASE)),
    ("<mega-menu-disclosure", re.compile(r"<\s*mega-menu-disclosure\b", re.IGNORECASE)),
    ("<facet-link", re.compile(r"<\s*facet-link\b", re.IGNORECASE)),
    ("<accordion-disclosure", re.compile(r"<\s*accordion-disclosure\b", re.IGNORECASE)),
    ("support.maestrooo.com", re.compile(r"support\.maestrooo\.com", re.IGNORECASE)),
    ("theme.js", re.compile(r"\btheme\.js\b", re.IGNORECASE)),
]

def scan_text(target: str, content: str, source: str):
    violations = []
    # Check filename
    if "theme.js" in os.path.basename(target).lower():
        violations.append((source, target, 0, "theme.js", "Filename matches theme.js"))
    for idx, line in enumerate(content.splitlines(), start=1):
        for token_name, regex in BANNED_TOKENS:
            if regex.search(line):
                violations.append((source, target, idx, token_name, line.strip()))
    return violations

def audit_remote_theme():
    print(f"[*] Starting independent GraphQL scan of theme: {THEME_ID}...")
    query = """
    query GetAllFiles($themeId: ID!, $cursor: String) {
      theme(id: $themeId) {
        id
        name
        role
        themeStoreId
        files(first: 50, after: $cursor) {
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
    total_remote = 0
    all_violations = []
    theme_info = {}

    while True:
        data, _, err = execute_shopify_graphql(query, {"themeId": THEME_ID, "cursor": cursor})
        if err or not data:
            print(f"[!] GraphQL error: {err}")
            sys.exit(1)

        theme = data.get("theme", {})
        if not theme_info:
            theme_info = {
                "name": theme.get("name"),
                "role": theme.get("role"),
                "themeStoreId": theme.get("themeStoreId"),
            }
            print(f"[*] Live Theme metadata: Name='{theme_info['name']}', Role='{theme_info['role']}', StoreID={theme_info['themeStoreId']}")

        files = theme.get("files", {})
        nodes = files.get("nodes", [])
        for n in nodes:
            total_remote += 1
            fname = n.get("filename", "")
            body = n.get("body") or {}
            content = body.get("content", "") or ""
            v = scan_text(fname, content, "remote")
            all_violations.extend(v)

        if files.get("pageInfo", {}).get("hasNextPage"):
            cursor = files.get("pageInfo", {}).get("endCursor")
        else:
            break

    print(f"[*] Total live remote files inspected: {total_remote}")
    return total_remote, all_violations, theme_info

def audit_local_staging():
    staging_dir = os.path.join(PROJECT_ROOT, "horizon_clean_theme")
    print(f"[*] Starting independent scan of local staging: {staging_dir}...")
    total_local = 0
    all_violations = []
    for root, dirs, files in os.walk(staging_dir):
        for f in files:
            path = os.path.join(root, f)
            rel = os.path.relpath(path, staging_dir)
            total_local += 1
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
                v = scan_text(rel, content, "local")
                all_violations.extend(v)
            except Exception as e:
                print(f"[!] Error reading {path}: {e}")
    print(f"[*] Total local staging files inspected: {total_local}")
    return total_local, all_violations

if __name__ == "__main__":
    remote_count, remote_violations, theme_info = audit_remote_theme()
    local_count, local_violations = audit_local_staging()

    print("\n" + "=" * 80)
    print("INDEPENDENT FORENSIC CLEAN-ROOM AUDIT RESULTS")
    print(f"Remote files: {remote_count} | Remote violations: {len(remote_violations)}")
    print(f"Local files:  {local_count}  | Local violations:  {len(local_violations)}")
    print(f"Theme Name: {theme_info.get('name')} (StoreId: {theme_info.get('themeStoreId')}, Role: {theme_info.get('role')})")
    print("=" * 80)

    all_v = remote_violations + local_violations
    if all_v:
        print(f"\n[!] VIOLATIONS DETECTED ({len(all_v)} total):")
        for src, target, line, tok, snip in all_v:
            print(f"  [{src.upper()}] {target}:{line} [{tok}] -> {snip[:100]}")
        sys.exit(1)
    else:
        print("\n[SUCCESS] 0 VIOLATIONS FOUND ACROSS ALL REMOTE AND LOCAL THEME ASSETS.")
        print("Banned tokens checked: maestrooo, <loading-bar, <mega-menu-disclosure, <facet-link, <accordion-disclosure, support.maestrooo.com, theme.js")
        sys.exit(0)
