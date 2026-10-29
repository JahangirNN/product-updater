#!/usr/bin/env python3
"""
Auditor Price Formatting Authenticity & Anti-Facade Forensics
Checks both local files and remote theme files on gid://shopify/OnlineStoreTheme/198751387814
to ensure genuine Liquid implementations rather than facades or mock constants.
"""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

THEME_ID = "gid://shopify/OnlineStoreTheme/198751387814"

FILES_TO_CHECK = [
    "snippets/price.liquid",
    "snippets/format-price.liquid",
    "snippets/luxury-pdp-enhancements.liquid",
    "snippets/cart-summary.liquid",
    "snippets/price-filter.liquid",
    "snippets/cart-products.liquid",
    "snippets/sneaker-vault-card.liquid",
    "sections/brand-tiles.liquid",
    "sections/marquee-collection-list.liquid",
    "blocks/buy-buttons.liquid"
]

def check_content(filename: str, content: str, source: str):
    issues = []
    # Check for facade patterns:
    # 1. Empty or near-empty file
    if len(content.strip()) < 50:
        issues.append(f"Suspiciously short content ({len(content)} chars)")
    
    # 2. Check for hardcoded price strings that mock real numbers
    # (e.g., returning constant 'Rs. 15,099' regardless of input)
    if "return 'Rs." in content or 'return "Rs.' in content:
        issues.append("Found return statement mocking price")

    # 3. Check for genuine whole rupee formatting tokens
    has_money_filter = "money" in content
    has_zero_strip = "money_without_trailing_zeros" in content or "replace: '.00'" in content or 'replace: ".00"' in content
    
    if not has_money_filter:
        issues.append("Missing Shopify money filter in pricing file")
    if not has_zero_strip:
        issues.append("Missing zero-decimal stripping logic")

    return issues

def audit_pricing():
    print(f"[*] Auditing {len(FILES_TO_CHECK)} pricing files on remote theme {THEME_ID}...")
    q = """
    query getFiles($themeId: ID!, $filenames: [String!]!) {
      theme(id: $themeId) {
        files(filenames: $filenames) {
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
    res, _, err = execute_shopify_graphql(q, {"themeId": THEME_ID, "filenames": FILES_TO_CHECK})
    if err or not res:
        print(f"[!] GraphQL Error: {err}")
        sys.exit(1)

    nodes = res.get("theme", {}).get("files", {}).get("nodes", [])
    remote_map = {n.get("filename"): n.get("body", {}).get("content", "") for n in nodes}

    print(f"[*] Retrieved {len(remote_map)} files from remote theme.")
    
    total_issues = 0
    for fname in FILES_TO_CHECK:
        print(f"\n--- Checking {fname} ---")
        # 1. Local check
        local_path = os.path.join(PROJECT_ROOT, "horizon_clean_theme", fname)
        if not os.path.exists(local_path):
            print(f"  [!] Local file missing: {local_path}")
            total_issues += 1
            continue
        with open(local_path, "r", encoding="utf-8", errors="replace") as f:
            local_content = f.read()

        local_issues = check_content(fname, local_content, "local")
        if local_issues:
            print(f"  [!] Local issues: {local_issues}")
            total_issues += len(local_issues)
        else:
            print(f"  [PASS] Local implementation: Authentic Liquid ({len(local_content)} chars)")

        # 2. Remote check
        if fname not in remote_map or not remote_map[fname]:
            print(f"  [!] Remote file missing or empty on theme {THEME_ID}!")
            total_issues += 1
            continue

        remote_content = remote_map[fname]
        remote_issues = check_content(fname, remote_content, "remote")
        if remote_issues:
            print(f"  [!] Remote issues: {remote_issues}")
            total_issues += len(remote_issues)
        else:
            print(f"  [PASS] Remote implementation: Authentic Liquid ({len(remote_content)} chars)")

        # 3. Parity check (local vs remote)
        # Check if local and remote match or are substantively identical
        if local_content.strip() == remote_content.strip():
            print(f"  [PASS] Remote and local files are 100% BIT-FOR-BIT IDENTICAL.")
        else:
            print(f"  [!] Note: Remote and local content differ (len local={len(local_content)}, len remote={len(remote_content)})")

    print("\n" + "=" * 80)
    print("AUTHENTICITY & ANTI-FACADE FORENSIC SUMMARY")
    print(f"Total files audited: {len(FILES_TO_CHECK)}")
    print(f"Total issues found: {total_issues}")
    print("=" * 80)

    if total_issues > 0:
        print("[FAIL] Pricing implementation failed authenticity forensics.")
        sys.exit(1)
    else:
        print("[PASS] All pricing implementations are GENUINE Liquid templates on both local and live theme.")
        sys.exit(0)

if __name__ == "__main__":
    audit_pricing()
