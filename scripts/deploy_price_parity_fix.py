"""
Deploy price parity fixes to live theme 197348655270.
Deploys snippets/product-card.liquid, snippets/sneaker-vault-card.liquid, snippets/price-list.liquid.
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
    ("snippets/product-card.liquid", os.path.join(PROJECT_ROOT, "theme", "snippets", "product-card.liquid")),
    ("snippets/sneaker-vault-card.liquid", os.path.join(PROJECT_ROOT, "theme", "snippets", "sneaker-vault-card.liquid")),
    ("snippets/price-list.liquid", os.path.join(PROJECT_ROOT, "theme", "snippets", "price-list.liquid")),
]

def deploy_price_parity():
    print("=" * 80)
    print(f"DEPLOYING PRICE PARITY FIX TO LIVE THEME {THEME_ID}")
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
    print("PRICE PARITY DEPLOYMENT COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    deploy_price_parity()
