import sys
import os
import json
import re

PROJECT_ROOT = r"c:\workspace\dropship-scraper-portable-20260905\product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

THEME_ID = "gid://shopify/OnlineStoreTheme/198751387814"

# 1. Fetch current header-group.json
query_get_header = """
{
  theme(id: "%s") {
    files(filenames: ["sections/header-group.json"]) {
      nodes {
        body {
          ... on OnlineStoreThemeFileBodyText {
            content
          }
        }
      }
    }
  }
}
""" % THEME_ID

res = execute_shopify_graphql(query_get_header)[0]
raw_header_content = res["theme"]["files"]["nodes"][0]["body"]["content"]

json_str = raw_header_content
if "/*" in json_str:
    json_str = re.sub(r"/\*.*?\*/", "", json_str, flags=re.DOTALL).strip()

header_data = json.loads(json_str)

# In Shopify Online Store 2.0 section groups, to disable a section:
# Set "disabled": true, or delete it from both "sections" and "order".
# Let's delete it completely from both "sections" and "order"!
if "header_announcements_9jGBFp" in header_data.get("sections", {}):
    del header_data["sections"]["header_announcements_9jGBFp"]

header_data["order"] = [sec for sec in header_data.get("order", []) if sec != "header_announcements_9jGBFp"]

updated_header_group_content = json.dumps(header_data, indent=2)

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
        "filename": "sections/header-group.json",
        "body": {
            "type": "TEXT",
            "value": updated_header_group_content
        }
    }
]

res = execute_shopify_graphql(mutation, variables={"themeId": THEME_ID, "files": files_to_deploy})
print("Deployment response for header-group.json:", res)
