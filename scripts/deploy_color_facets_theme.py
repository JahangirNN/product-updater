"""
Deploy updated facets.liquid, active-facets.liquid, theme.css, and theme.js to live Shopify theme #197348655270.
Uses GraphQL themeFilesUpsert mutation.
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

FILES_TO_DEPLOY = [
    ("snippets/facets.liquid", os.path.join(PROJECT_ROOT, "theme", "snippets", "facets.liquid")),
    ("snippets/active-facets.liquid", os.path.join(PROJECT_ROOT, "theme", "snippets", "active-facets.liquid")),
    ("assets/theme.css", os.path.join(PROJECT_ROOT, "theme", "assets", "theme.css")),
    ("assets/theme.js", os.path.join(PROJECT_ROOT, "theme", "assets", "theme.js")),
]

def deploy_color_facets_theme():
    print("=" * 80)
    print(f"DEPLOYING COLOR FACET THEME FILES TO LIVE THEME {THEME_ID}")
    print("=" * 80)

    for rel_path, abs_path in FILES_TO_DEPLOY:
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"Deploying {rel_path} ({len(content)} bytes)...")
        file_payload = [{
            "filename": rel_path,
            "body": {
                "type": "TEXT",
                "value": content
            }
        }]
        data, ext, err = execute_shopify_graphql(
            THEME_FILES_MUTATION,
            variables={"files": file_payload, "themeId": THEME_ID}
        )
        if data and "themeFilesUpsert" in data:
            result = data["themeFilesUpsert"]
            errors = result.get("userErrors", [])
            if errors:
                print(f"  UserErrors on {rel_path}: {errors}")
            else:
                upserted = result.get("upsertedThemeFiles", [])
                print(f"  SUCCESS: Upserted {[f['filename'] for f in upserted]}")
        else:
            print(f"  GraphQL Error on {rel_path}: {err}")
        time.sleep(1)

    print("=" * 80)
    print("THEME DEPLOYMENT COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    deploy_color_facets_theme()
