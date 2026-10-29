"""
Deploy iPad Mini and responsive header fixes to live Horizon theme (gid://shopify/OnlineStoreTheme/198751387814).
"""
import os
import sys

PROJECT_ROOT = r"c:\workspace\dropship-scraper-portable-20260905\product-updater"
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

def deploy_header_fixes():
    files_to_deploy = [
        ("sections/header.liquid", os.path.join(PROJECT_ROOT, "horizon_clean_theme", "sections", "header.liquid")),
        ("assets/utilities.js", os.path.join(PROJECT_ROOT, "horizon_clean_theme", "assets", "utilities.js")),
    ]

    payload = []
    for theme_filename, local_path in files_to_deploy:
        with open(local_path, "r", encoding="utf-8") as f:
            content = f.read()
        payload.append({
            "filename": theme_filename,
            "body": {
                "type": "TEXT",
                "value": content
            }
        })
        print(f"Prepared {theme_filename} ({len(content)} chars)")

    print(f"\nDeploying {len(payload)} files to theme {THEME_ID}...")
    data, resp, err = execute_shopify_graphql(THEME_FILES_MUTATION, {
        "themeId": THEME_ID,
        "files": payload
    })

    if err:
        print("ERROR executing GraphQL:", err)
        sys.exit(1)

    result = data.get("themeFilesUpsert", {})
    user_errors = result.get("userErrors", [])
    if user_errors:
        print("USER ERRORS:")
        for ue in user_errors:
            print(" -", ue)
        sys.exit(1)

    upserted = result.get("upsertedThemeFiles", [])
    print(f"Successfully upserted {len(upserted)} theme files:")
    for uf in upserted:
        print("  ✓", uf.get("filename"))

if __name__ == "__main__":
    deploy_header_fixes()
