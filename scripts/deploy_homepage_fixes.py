"""
Deploy updated homepage sections, snippets, and templates to live Shopify theme #197348655270.
Deploys:
  - sections/collection-list.liquid
  - sections/marquee-collection-list.liquid
  - sections/media-grid.liquid
  - snippets/product-card.liquid
  - templates/index.json
Uses GraphQL themeFilesUpsert mutation.
"""
import os
import sys
import json
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

FILES_TO_DEPLOY = [
    ("sections/collection-list.liquid", os.path.join(PROJECT_ROOT, "theme", "sections", "collection-list.liquid")),
    ("sections/marquee-collection-list.liquid", os.path.join(PROJECT_ROOT, "theme", "sections", "marquee-collection-list.liquid")),
    ("sections/media-grid.liquid", os.path.join(PROJECT_ROOT, "theme", "sections", "media-grid.liquid")),
    ("snippets/product-card.liquid", os.path.join(PROJECT_ROOT, "theme", "snippets", "product-card.liquid")),
    ("templates/index.json", os.path.join(PROJECT_ROOT, "theme", "templates", "index.json")),
]

def deploy_homepage_fixes():
    print("=" * 80)
    print(f"DEPLOYING HOMEPAGE RECTIFICATIONS TO THEME {THEME_ID}")
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
        print(f"Attempt {attempt} result: err={err}. Retrying in 2 seconds...")
        time.sleep(2)

    if err or not data:
        print(f"FAILED to deploy theme files: {err}")
        return False

    upsert_result = data.get("themeFilesUpsert", {})
    user_errors = upsert_result.get("userErrors", [])
    if user_errors:
        print(f"UserErrors during deploy: {user_errors}")
        return False

    upserted = upsert_result.get("upsertedThemeFiles", [])
    print("SUCCESSFULLY UPSERTED THEME FILES:")
    for uf in upserted:
        print(f"  + {uf.get('filename')}")
    return True

if __name__ == "__main__":
    success = deploy_homepage_fixes()
    sys.exit(0 if success else 1)
