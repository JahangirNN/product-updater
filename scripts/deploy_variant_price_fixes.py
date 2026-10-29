"""
Deploy variant price synchronization fixes to live Shopify theme (Horizon #198751387814).
Deploys:
  - snippets/product-card-variants.liquid
  - snippets/product-card.liquid
  - snippets/variant-main-picker.liquid
  - snippets/luxury-pdp-enhancements.liquid
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
    ("snippets/product-card-variants.liquid", os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "product-card-variants.liquid")),
    ("snippets/product-card.liquid", os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "product-card.liquid")),
    ("snippets/variant-main-picker.liquid", os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "variant-main-picker.liquid")),
    ("snippets/luxury-pdp-enhancements.liquid", os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "luxury-pdp-enhancements.liquid")),
]

def main():
    print(f"Deploying variant price synchronization files to theme {THEME_ID}...")
    files_input = []
    for theme_path, local_path in FILES_TO_DEPLOY:
        if not os.path.isfile(local_path):
            print(f"File not found: {local_path}")
            sys.exit(1)
        with open(local_path, "r", encoding="utf-8") as f:
            content = f.read()
        files_input.append({
            "filename": theme_path,
            "body": {
                "type": "TEXT",
                "value": content
            }
        })
        print(f"Prepared {theme_path} ({len(content)} chars)")

    variables = {
        "themeId": THEME_ID,
        "files": files_input
    }

    data, ext, err = None, None, None
    for attempt in range(1, 4):
        print(f"GraphQL themeFilesUpsert attempt {attempt}...")
        data, ext, err = execute_shopify_graphql(THEME_FILES_MUTATION, variables=variables)
        if data and "themeFilesUpsert" in data:
            break
        print(f"Retrying... err={err}")

    if not data or "themeFilesUpsert" not in data:
        print(f"Failed after retries: data={data}, err={err}")
        sys.exit(1)

    res = data.get("themeFilesUpsert", {})
    u_errs = res.get("userErrors", [])
    if u_errs:
        print(f"GraphQL UserErrors: {u_errs}")
        sys.exit(1)

    upserted = [u["filename"] for u in res.get("upsertedThemeFiles", [])]
    print(f"Successfully deployed {len(upserted)} files: {upserted}")

if __name__ == "__main__":
    main()
