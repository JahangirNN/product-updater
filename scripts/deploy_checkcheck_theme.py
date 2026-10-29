"""
Deploy CheckCheck integration snippet, assets, and updated product-info.liquid to live Shopify theme #197348655270.
"""
import os
import sys
import base64
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql
from storage.logger import log_info, log_success, log_error

THEME_ID = "gid://shopify/OnlineStoreTheme/197348655270"

THEME_FILES_MUTATION = """
mutation themeFilesUpsert($files: [OnlineStoreThemeFilesUpsertFileInput!]!, $themeId: ID!) {
  themeFilesUpsert(files: $files, themeId: $themeId) {
    upsertedThemeFiles {
      filename
    }
    userErrors {
      field
      message
    }
  }
}
"""

TEXT_FILES = [
    ("snippets/checkcheck-authenticity.liquid", os.path.join(PROJECT_ROOT, "theme", "snippets", "checkcheck-authenticity.liquid")),
    ("snippets/product-info.liquid", os.path.join(PROJECT_ROOT, "theme", "snippets", "product-info.liquid")),
    ("assets/checkcheck-logo.svg", os.path.join(PROJECT_ROOT, "theme", "assets", "checkcheck-logo.svg")),
    ("assets/checkcheck-wordmark.svg", os.path.join(PROJECT_ROOT, "theme", "assets", "checkcheck-wordmark.svg")),
]

BINARY_FILES = [
    ("assets/checkcheck-badge-dark.png", os.path.join(PROJECT_ROOT, "theme", "assets", "checkcheck-badge-dark.png")),
    ("assets/checkcheck-badge-green.png", os.path.join(PROJECT_ROOT, "theme", "assets", "checkcheck-badge-green.png")),
]

def main():
    print("=" * 72)
    print("DEPLOYING CHECKCHECK ASSETS & SNIPPETS TO LIVE THEME")
    print(f"Target Theme: {THEME_ID}")
    print("=" * 72)

    files_payload = []
    
    # 1. Text / SVG files
    for rel_path, abs_path in TEXT_FILES:
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
        files_payload.append({
            "filename": rel_path,
            "body": {
                "type": "TEXT",
                "value": content
            }
        })
        print(f"Prepared TEXT: {rel_path} ({len(content)} bytes)")
        
    # 2. Binary PNG files
    for rel_path, abs_path in BINARY_FILES:
        with open(abs_path, "rb") as f:
            b64_content = base64.b64encode(f.read()).decode("utf-8")
        files_payload.append({
            "filename": rel_path,
            "body": {
                "type": "BASE64",
                "value": b64_content
            }
        })
        print(f"Prepared BASE64: {rel_path} ({len(b64_content)} chars)")

    # Execute GraphQL Mutation
    print("\nExecuting GraphQL themeFilesUpsert...")
    data, ext, err = None, None, None
    for attempt in range(1, 4):
        print(f"Attempt {attempt}/3...")
        data, ext, err = execute_shopify_graphql(
            THEME_FILES_MUTATION,
            variables={
                "themeId": THEME_ID,
                "files": files_payload
            }
        )
        if data and not err:
            break
        print(f"Attempt {attempt} failed: {err}. Retrying in 2 seconds...")
        time.sleep(2)

    if err or not data:
        print(f"FAILED to deploy theme files: {err}")
        return False

    res = data.get("themeFilesUpsert", {})
    u_errs = res.get("userErrors", [])
    if u_errs:
        print(f"UserErrors deploying theme files: {u_errs}")
        return False

    upserted = res.get("upsertedThemeFiles", [])
    print(f"\nSUCCESS! {len(upserted)} theme files deployed to live theme {THEME_ID}:")
    for uf in upserted:
        print(f"  [OK] {uf.get('filename')}")
    print("=" * 72)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
