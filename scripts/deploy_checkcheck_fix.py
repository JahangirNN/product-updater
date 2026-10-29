import sys
import os

PROJECT_ROOT = r"c:\workspace\dropship-scraper-portable-20260905\product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

THEME_ID = "gid://shopify/OnlineStoreTheme/198751387814"

buy_buttons_path = os.path.join(PROJECT_ROOT, "horizon_clean_theme", "blocks", "buy-buttons.liquid")
with open(buy_buttons_path, "r", encoding="utf-8") as f:
    bb_content = f.read()

cc_path = os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "checkcheck-authenticity.liquid")
with open(cc_path, "r", encoding="utf-8") as f:
    cc_content = f.read()

mutation = """
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

files_to_deploy = [
    {
        "filename": "blocks/buy-buttons.liquid",
        "body": {
            "type": "TEXT",
            "value": bb_content
        }
    },
    {
        "filename": "snippets/checkcheck-authenticity.liquid",
        "body": {
            "type": "TEXT",
            "value": cc_content
        }
    }
]

res = execute_shopify_graphql(mutation, variables={"themeId": THEME_ID, "files": files_to_deploy})
print("Deployment response for buy-buttons and checkcheck:", res)
