"""
Deploy updated navigation snippets to live Shopify theme #197348655270.
Deploys:
  - snippets/luxury-desktop-nav.liquid
  - snippets/luxury-sidebar-panels.liquid
  - snippets/facets.liquid
Uses GraphQL themeFilesUpsert mutation.
"""
import os
import sys
import json

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

FILES_TO_DEPLOY = [
    ("sections/header.liquid", os.path.join(PROJECT_ROOT, "theme", "sections", "header.liquid")),
    ("sections/collection-banner.liquid", os.path.join(PROJECT_ROOT, "theme", "sections", "collection-banner.liquid")),
    ("sections/newsletter-popup.liquid", os.path.join(PROJECT_ROOT, "theme", "sections", "newsletter-popup.liquid")),
    ("snippets/luxury-desktop-nav.liquid", os.path.join(PROJECT_ROOT, "theme", "snippets", "luxury-desktop-nav.liquid")),
    ("snippets/luxury-sidebar-panels.liquid", os.path.join(PROJECT_ROOT, "theme", "snippets", "luxury-sidebar-panels.liquid")),
    ("snippets/facets.liquid", os.path.join(PROJECT_ROOT, "theme", "snippets", "facets.liquid")),
    ("snippets/active-facets.liquid", os.path.join(PROJECT_ROOT, "theme", "snippets", "active-facets.liquid")),
    ("snippets/product-card.liquid", os.path.join(PROJECT_ROOT, "theme", "snippets", "product-card.liquid")),
    ("snippets/product-card-horizontal.liquid", os.path.join(PROJECT_ROOT, "theme", "snippets", "product-card-horizontal.liquid")),
    ("snippets/vendor.liquid", os.path.join(PROJECT_ROOT, "theme", "snippets", "vendor.liquid")),
    ("snippets/product-info.liquid", os.path.join(PROJECT_ROOT, "theme", "snippets", "product-info.liquid")),
    ("snippets/css-variables.liquid", os.path.join(PROJECT_ROOT, "theme", "snippets", "css-variables.liquid")),
    ("snippets/luxury-breadcrumbs.liquid", os.path.join(PROJECT_ROOT, "theme", "snippets", "luxury-breadcrumbs.liquid")),
    ("snippets/product-badges.liquid", os.path.join(PROJECT_ROOT, "theme", "snippets", "product-badges.liquid")),
    ("sections/main-search.liquid", os.path.join(PROJECT_ROOT, "theme", "sections", "main-search.liquid")),
    ("config/settings_data.json", os.path.join(PROJECT_ROOT, "theme", "config", "settings_data.json")),
    ("assets/theme.js", os.path.join(PROJECT_ROOT, "theme", "assets", "theme.js")),
]

def deploy_snippets():
    print("=" * 80)
    print(f"DEPLOYING NAVIGATION SNIPPETS TO THEME {THEME_ID}")
    print("=" * 80)

    files_payload = []
    for rel_path, abs_path in FILES_TO_DEPLOY:
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
        files_payload.append({
            "filename": rel_path,
            "body": {
                "type": "TEXT",
                "value": content
            }
        })
        print(f"Prepared {rel_path} ({len(content)} bytes)")

    import time
    data, ext, err = None, None, None
    for attempt in range(1, 4):
        print(f"Deploy attempt {attempt}/3...")
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
    print("\nSUCCESS! Successfully deployed snippets:")
    for uf in upserted:
        print(f"  - {uf.get('filename')}")
    print("=" * 80)
    return True

if __name__ == "__main__":
    deploy_snippets()
