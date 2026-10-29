import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

THEME_ID = "gid://shopify/OnlineStoreTheme/197348655270"

snippet_path = os.path.join(PROJECT_ROOT, "theme", "snippets", "luxury-pdp-enhancements.liquid")
with open(snippet_path, "r", encoding="utf-8") as f:
    content = f.read()

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

variables = {
    "themeId": THEME_ID,
    "files": [{
        "filename": "snippets/luxury-pdp-enhancements.liquid",
        "body": {
            "type": "TEXT",
            "value": content
        }
    }]
}

data, ext, err = execute_shopify_graphql(mutation, variables)
if err:
    print("Error:", err)
else:
    res = data.get("themeFilesUpsert", {})
    errs = res.get("userErrors", [])
    if errs:
        print("UserErrors:", errs)
    else:
        print("Successfully deployed snippets/luxury-pdp-enhancements.liquid to live theme!")
