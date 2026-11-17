import os
import sys
import json
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

THEME_ID = "gid://shopify/OnlineStoreTheme/198751387814"

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
    ("snippets/luxury-footer-concierge.liquid", os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "luxury-footer-concierge.liquid")),
    ("sections/footer.liquid", os.path.join(PROJECT_ROOT, "horizon_clean_theme", "sections", "footer.liquid")),
    ("snippets/luxury_sidebar_navigation.liquid", os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "luxury_sidebar_navigation.liquid")),
    ("snippets/luxury-pdp-enhancements.liquid", os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "luxury-pdp-enhancements.liquid")),
    ("templates/page.contact.json", os.path.join(PROJECT_ROOT, "horizon_clean_theme", "templates", "page.contact.json")),
]

def deploy():
    print("=" * 80)
    print(f"DEPLOYING CONCIERGE & CONTACT THEME FILES TO THEME {THEME_ID}")
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
        print(f"\nDeploy attempt {attempt}/3...")
        data, ext, err = execute_shopify_graphql(
            THEME_FILES_MUTATION,
            variables={
                "themeId": THEME_ID,
                "files": files_payload
            }
        )
        if not err and data and data.get("themeFilesUpsert"):
            break
        print(f"Attempt {attempt} encountered error: {err}. Retrying in 3s...")
        time.sleep(3)

    if err or not data or not data.get("themeFilesUpsert"):
        print(f"\n[FATAL] Deployment failed: {err}")
        sys.exit(1)

    result = data["themeFilesUpsert"]
    user_errors = result.get("userErrors", [])
    if user_errors:
        print(f"\n[ERROR] GraphQL userErrors: {json.dumps(user_errors, indent=2)}")
        sys.exit(1)

    upserted = result.get("upsertedThemeFiles", [])
    print(f"\n[SUCCESS] Successfully deployed {len(upserted)} theme files:")
    for f in upserted:
        print(f"  ✓ {f.get('filename')}")
    print("=" * 80)

if __name__ == "__main__":
    deploy()
