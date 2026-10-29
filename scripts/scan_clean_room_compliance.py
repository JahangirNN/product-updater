#!/usr/bin/env python3
"""
Clean-Room & Anti-Copyright Compliance Scanner
Target: The Rare Avenue Quiet Luxury Storefront Rebuild onto Horizon
Theme GID: gid://shopify/OnlineStoreTheme/198751387814

Verifies zero occurrences of prohibited Maestrooo / Prestige proprietary tokens:
1. maestrooo
2. <loading-bar>
3. <mega-menu-disclosure>
4. <facet-link>
5. support.maestrooo.com
6. theme.js

Usage:
    python scripts/scan_clean_room_compliance.py [--remote] [--theme-id ID] [--path PATH] [--all]
    
Exit Codes:
    0: Clean room verified - 0 violations found
    1: Compliance violation detected or scan failure
"""

import os
import sys
import argparse
import time
import re
from typing import List, Dict, Any, Tuple, Optional

# Ensure UTF-8 stdout encoding on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from storage.shopify_auth import execute_shopify_graphql
    SHOPIFY_AUTH_AVAILABLE = True
except ImportError:
    SHOPIFY_AUTH_AVAILABLE = False

DEFAULT_THEME_ID = "gid://shopify/OnlineStoreTheme/198751387814"

PROHIBITED_TOKENS = [
    "maestrooo",
    "<loading-bar>",
    "<mega-menu-disclosure>",
    "<facet-link>",
    "support.maestrooo.com",
    "theme.js"
]

# Patterns for exact/tag matching
TOKEN_PATTERNS = {
    "maestrooo": re.compile(r"maestrooo", re.IGNORECASE),
    "<loading-bar>": re.compile(r"<\s*loading-bar\b", re.IGNORECASE),
    "<mega-menu-disclosure>": re.compile(r"<\s*mega-menu-disclosure\b", re.IGNORECASE),
    "<facet-link>": re.compile(r"<\s*facet-link\b", re.IGNORECASE),
    "support.maestrooo.com": re.compile(r"support\.maestrooo\.com", re.IGNORECASE),
    "theme.js": re.compile(r"\btheme\.js\b", re.IGNORECASE)
}

TEXT_EXTENSIONS = {
    ".liquid", ".json", ".js", ".css", ".scss", ".html", ".htm",
    ".svg", ".txt", ".md", ".xml", ".yml", ".yaml"
}


class ComplianceViolation:
    def __init__(self, target: str, source: str, line_num: int, token: str, snippet: str):
        self.target = target      # e.g., filename or remote path
        self.source = source      # 'remote' or 'local'
        self.line_num = line_num  # 0 if filename-only
        self.token = token
        self.snippet = snippet

    def __str__(self) -> str:
        if self.line_num > 0:
            return f"[{self.source.upper()}] {self.target}:{self.line_num} -> Match '{self.token}': {self.snippet[:120]}"
        return f"[{self.source.upper()}] {self.target} -> Filename match '{self.token}'"


def scan_text_content(target_name: str, content: str, source: str) -> List[ComplianceViolation]:
    """Scan string content line by line against prohibited tokens."""
    violations: List[ComplianceViolation] = []
    
    # 1. Check filename itself
    basename = os.path.basename(target_name).lower()
    if basename == "theme.js" or "theme.js" in basename:
        violations.append(ComplianceViolation(
            target=target_name,
            source=source,
            line_num=0,
            token="theme.js",
            snippet=f"Filename matches prohibited bundle '{basename}'"
        ))

    # 2. Check lines
    for line_idx, line in enumerate(content.splitlines(), start=1):
        for token_name, pattern in TOKEN_PATTERNS.items():
            if pattern.search(line):
                violations.append(ComplianceViolation(
                    target=target_name,
                    source=source,
                    line_num=line_idx,
                    token=token_name,
                    snippet=line.strip()
                ))

    return violations


def scan_local_directory(dir_path: str, excludes: Optional[List[str]] = None) -> Tuple[int, List[ComplianceViolation]]:
    """Recursively scan a local directory for prohibited tokens."""
    if excludes is None:
        excludes = [".git", "node_modules", "__pycache__", ".pytest_cache", ".agents"]

    file_count = 0
    violations: List[ComplianceViolation] = []

    if not os.path.exists(dir_path):
        print(f"[-] Local path not found: {dir_path}")
        return 0, violations

    if os.path.isfile(dir_path):
        file_count = 1
        ext = os.path.splitext(dir_path)[1].lower()
        if ext in TEXT_EXTENSIONS:
            try:
                with open(dir_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                violations.extend(scan_text_content(dir_path, content, "local"))
            except Exception as e:
                print(f"[!] Error reading file {dir_path}: {e}")
        return file_count, violations

    for root, dirs, files in os.walk(dir_path):
        # Prune excluded directories
        dirs[:] = [d for d in dirs if d not in excludes]

        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in TEXT_EXTENSIONS:
                continue

            file_path = os.path.join(root, fname)
            file_count += 1
            rel_path = os.path.relpath(file_path, dir_path)

            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                file_violations = scan_text_content(rel_path, content, "local")
                violations.extend(file_violations)
            except Exception as e:
                print(f"[!] Error reading {file_path}: {e}")

    return file_count, violations


def scan_remote_shopify_theme(theme_id: str) -> Tuple[int, List[ComplianceViolation]]:
    """Scan all files of a Shopify theme via Admin GraphQL API."""
    if not SHOPIFY_AUTH_AVAILABLE:
        raise RuntimeError("storage.shopify_auth is not available in environment.")

    print(f"[*] Querying Shopify Admin GraphQL for theme: {theme_id}...")

    query = """
    query GetThemeFiles($themeId: ID!, $cursor: String) {
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
    file_count = 0
    violations: List[ComplianceViolation] = []
    theme_info = {}

    page = 1
    while True:
        variables: Dict[str, Any] = {"themeId": theme_id}
        if cursor:
            variables["cursor"] = cursor

        data, ext, err = execute_shopify_graphql(query, variables=variables)
        if err or not data:
            raise RuntimeError(f"GraphQL error fetching theme files: {err}")

        theme_node = data.get("theme")
        if not theme_node:
            raise RuntimeError(f"Theme not found with ID {theme_id}. GraphQL returned: {data}")

        if not theme_info:
            theme_info = {
                "name": theme_node.get("name"),
                "role": theme_node.get("role"),
                "themeStoreId": theme_node.get("themeStoreId")
            }
            print(f"[*] Connected to Theme: {theme_info['name']} (role: {theme_info['role']}, storeId: {theme_info['themeStoreId']})")

        files_conn = theme_node.get("files", {})
        nodes = files_conn.get("nodes", [])

        for node in nodes:
            file_count += 1
            filename = node.get("filename", "")
            body = node.get("body")
            content = body.get("content", "") if body else ""

            v_list = scan_text_content(filename, content, "remote")
            violations.extend(v_list)

        page_info = files_conn.get("pageInfo", {})
        if page_info.get("hasNextPage"):
            cursor = page_info.get("endCursor")
            page += 1
        else:
            break

    return file_count, violations


def run_compliance_scan(
    remote: bool = False,
    theme_id: str = DEFAULT_THEME_ID,
    local_path: Optional[str] = None
) -> int:
    """Run full compliance scanner and return exit code (0 = clean, 1 = violations)."""
    start_time = time.time()
    print("=" * 80)
    print("THE RARE AVENUE - CLEAN-ROOM & ANTI-COPYRIGHT COMPLIANCE SCANNER")
    print(f"Target Theme GID: {theme_id}")
    print(f"Prohibited Tokens: {', '.join(PROHIBITED_TOKENS)}")
    print("=" * 80)

    total_scanned = 0
    all_violations: List[ComplianceViolation] = []

    # 1. Remote Scan
    if remote:
        try:
            print(f"\n[PHASE 1] Remote Shopify Theme Inspection ({theme_id})")
            r_count, r_violations = scan_remote_shopify_theme(theme_id)
            total_scanned += r_count
            all_violations.extend(r_violations)
            print(f" -> Scanned {r_count} remote theme files. Found {len(r_violations)} violation(s).")
        except Exception as e:
            print(f"[!] FAILED remote theme scan: {e}")
            return 1

    # 2. Local Scan
    if local_path:
        print(f"\n[PHASE 2] Local Directory Inspection ({local_path})")
        l_count, l_violations = scan_local_directory(local_path)
        total_scanned += l_count
        all_violations.extend(l_violations)
        print(f" -> Scanned {l_count} local files. Found {len(l_violations)} violation(s).")

    duration = time.time() - start_time

    # Results & Reporting
    print("\n" + "=" * 80)
    print(f"COMPLIANCE SCAN REPORT (Elapsed: {duration:.2f}s)")
    print(f"Total Files Inspected: {total_scanned}")
    print(f"Total Prohibited Token Violations: {len(all_violations)}")
    print("=" * 80)

    if all_violations:
        print("\n[CRITICAL VIOLATION DETECTED] Prohibited code patterns found:")
        for idx, v in enumerate(all_violations, start=1):
            print(f"  {idx}. {v}")
        print("\nResult: FAIL (Exit Code 1)")
        return 1

    print("\n[CLEAN-ROOM CERTIFICATION: PASS]")
    print("0 occurrences of Maestrooo/Prestige proprietary tokens found.")
    print("All inspected files strictly conform to ADR 0030 Clean-Room Architecture.")
    print("Exit Code: 0\n")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Verify zero occurrences of prohibited proprietary code tokens across theme files."
    )
    parser.add_argument(
        "--remote",
        action="store_true",
        help="Scan live theme files from Shopify Admin GraphQL API."
    )
    parser.add_argument(
        "--theme-id",
        type=str,
        default=DEFAULT_THEME_ID,
        help=f"Shopify Theme GID to inspect (default: {DEFAULT_THEME_ID})."
    )
    parser.add_argument(
        "--path",
        type=str,
        default=None,
        help="Local file or directory path to scan."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Scan both remote Shopify theme and local theme directory."
    )

    args = parser.parse_args()

    # Determine mode
    scan_remote = args.remote or args.all
    local_path = args.path

    if args.all and not local_path:
        local_path = os.path.join(PROJECT_ROOT, "theme")

    # If neither flag specified, default to remote scan of default theme
    if not scan_remote and not local_path:
        scan_remote = True

    exit_code = run_compliance_scan(
        remote=scan_remote,
        theme_id=args.theme_id,
        local_path=local_path
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
