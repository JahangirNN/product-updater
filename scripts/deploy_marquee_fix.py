"""
Deploy optimized marquee-collection-list.liquid to live Shopify theme 197348655270.
Restores hardware-accelerated pure GPU compositor continuous scrolling, eliminates JS RAF lag,
and preserves 4-piece studio gallery thumbnails and drag interactions.
"""
import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

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

TARGET_SECTION = "sections/marquee-collection-list.liquid"
LOCAL_PATH = os.path.join(PROJECT_ROOT, "theme", TARGET_SECTION)

def deploy():
    print("=" * 80)
    print(f"DEPLOYING MARQUEE SECTION FIX TO LIVE THEME: {THEME_ID}")
    print("=" * 80)

    if not os.path.exists(LOCAL_PATH):
        print(f"Error: File not found at {LOCAL_PATH}")
        sys.exit(1)

    with open(LOCAL_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    print(f"Read {TARGET_SECTION} ({len(content)} bytes, {len(content.splitlines())} lines)")

    file_payload = [{
        "filename": TARGET_SECTION,
        "body": {
            "type": "TEXT",
            "value": content
        }
    }]

    print("Sending GraphQL themeFilesUpsert mutation...")
    data, ext, err = execute_shopify_graphql(
        THEME_FILES_MUTATION,
        variables={"files": file_payload, "themeId": THEME_ID}
    )

    if err or not data:
        print(f"GraphQL Execution Error: {err}")
        sys.exit(1)

    result = data.get("themeFilesUpsert", {})
    user_errors = result.get("userErrors", [])
    if user_errors:
        print(f"UserErrors returned: {user_errors}")
        sys.exit(1)

    upserted = result.get("upsertedThemeFiles", [])
    print(f"Successfully upserted: {[u['filename'] for u in upserted]}")
    print("=" * 80)
    print("DEPLOYMENT COMPLETE! Section is live on https://therareavenue.com/")
    print("=" * 80)

if __name__ == "__main__":
    deploy()
