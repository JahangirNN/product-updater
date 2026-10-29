"""
Deploy refined PLP collection hero banner fixes to live theme 197348655270.
Deploys:
  - sections/collection-banner.liquid
  - templates/collection.json
  - assets/theme.css
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
    ("sections/collection-banner.liquid", os.path.join(PROJECT_ROOT, "theme", "sections", "collection-banner.liquid")),
    ("templates/collection.json", os.path.join(PROJECT_ROOT, "theme", "templates", "collection.json")),
    ("assets/theme.css", os.path.join(PROJECT_ROOT, "theme", "assets", "theme.css")),
]

def deploy_plp_hero_banner():
    print("=" * 80)
    print(f"DEPLOYING REFINED PLP HERO BANNER TO LIVE THEME {THEME_ID}")
    print("=" * 80)

    success_count = 0
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
                success_count += 1
        else:
            print(f"  GraphQL Error on {rel_path}: {err}")
        time.sleep(1)

    print("=" * 80)
    print(f"PLP HERO BANNER DEPLOYMENT COMPLETED ({success_count}/{len(FILES_TO_DEPLOY)} SUCCESS)")
    print("=" * 80)
    return success_count == len(FILES_TO_DEPLOY)

if __name__ == "__main__":
    ok = deploy_plp_hero_banner()
    if not ok:
        sys.exit(1)
