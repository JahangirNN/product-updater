"""
Deploy PDP and PLP Filter Enhancements to Live Shopify Theme #198751387814 (Horizon).
Deploys:
  - sections/product-list.liquid (PDP Discovery Filters on product list)
  - sections/product-recommendations.liquid (PDP Discovery Filters on recommendations)
  - blocks/filters.liquid (PLP Gender & Multi-Brand Filters with Availability suppressed)
"""
import os
import sys

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
    ("sections/product-list.liquid", os.path.join(PROJECT_ROOT, "theme", "sections", "product-list.liquid")),
    ("sections/product-recommendations.liquid", os.path.join(PROJECT_ROOT, "theme", "sections", "product-recommendations.liquid")),
    ("blocks/filters.liquid", os.path.join(PROJECT_ROOT, "theme", "blocks", "filters.liquid")),
]

def deploy():
    print(f"Deploying {len(FILES_TO_DEPLOY)} theme files to live theme {THEME_ID}...")
    files_payload = []
    for fname, fpath in FILES_TO_DEPLOY:
        if not os.path.exists(fpath):
            print(f"ERROR: File not found: {fpath}")
            return False
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        files_payload.append({
            "filename": fname,
            "body": {
                "type": "TEXT",
                "value": content
            }
        })
        print(f"  * Prepared {fname} ({len(content)} chars)")

    data, resp, err = execute_shopify_graphql(THEME_FILES_MUTATION, variables={
        "files": files_payload,
        "themeId": THEME_ID
    })

    if err:
        print(f"ERROR: {err}")
        return False

    upsert_res = data.get("themeFilesUpsert", {})
    user_errors = upsert_res.get("userErrors", [])
    if user_errors:
        print(f"GraphQL userErrors: {user_errors}")
        return False

    upserted = upsert_res.get("upsertedThemeFiles", [])
    print(f"SUCCESS: Successfully upserted {len(upserted)} files:")
    for uf in upserted:
        print(f"  + {uf.get('filename')}")
    return True

if __name__ == "__main__":
    success = deploy()
    sys.exit(0 if success else 1)
