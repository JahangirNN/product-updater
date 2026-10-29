"""
Deploy swatch variant fix, CheckCheck bundle fix, and product-form.js to live Horizon theme.
Theme ID: gid://shopify/OnlineStoreTheme/198751387814
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

FILES_TO_DEPLOY = [
    ("snippets/cart-products.liquid", os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "cart-products.liquid")),
    ("snippets/cart-summary.liquid", os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "cart-summary.liquid")),
    ("snippets/cart-bubble.liquid", os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "cart-bubble.liquid")),
    ("assets/component-cart-items.js", os.path.join(PROJECT_ROOT, "horizon_clean_theme", "assets", "component-cart-items.js")),
    ("assets/cart-icon.js", os.path.join(PROJECT_ROOT, "horizon_clean_theme", "assets", "cart-icon.js")),
    ("assets/product-form.js", os.path.join(PROJECT_ROOT, "horizon_clean_theme", "assets", "product-form.js")),
    ("blocks/buy-buttons.liquid", os.path.join(PROJECT_ROOT, "horizon_clean_theme", "blocks", "buy-buttons.liquid")),
    ("snippets/variant-main-picker.liquid", os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "variant-main-picker.liquid")),
    ("snippets/luxury-pdp-enhancements.liquid", os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "luxury-pdp-enhancements.liquid")),
]

def deploy():
    print(f"Deploying to Theme ID: {THEME_ID}...")
    files_input = []
    for theme_path, local_path in FILES_TO_DEPLOY:
        if not os.path.isfile(local_path):
            print(f"Error: file not found: {local_path}")
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
        print(f"Loaded {theme_path}: {len(content)} characters")

    variables = {
        "themeId": THEME_ID,
        "files": files_input
    }

    print("Executing themeFilesUpsert GraphQL mutation...")
    data, ext, err = execute_shopify_graphql(THEME_FILES_MUTATION, variables=variables)

    if err or not data:
        print(f"Failed to deploy: {err}")
        sys.exit(1)

    result = data.get("themeFilesUpsert", {})
    user_errors = result.get("userErrors", [])
    if user_errors:
        print("User errors:", user_errors)
        sys.exit(1)

    upserted = [f["filename"] for f in result.get("upsertedThemeFiles", [])]
    print(f"Successfully upserted {len(upserted)} theme files: {upserted}")

if __name__ == "__main__":
    deploy()
