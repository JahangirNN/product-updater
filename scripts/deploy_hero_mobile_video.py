"""
Deploy responsive 9:16 mobile hero video to live Shopify theme 197348655270.
Deploys:
  - sections/slideshow.liquid
  - templates/index.json
"""
import os
import sys
import base64
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

def deploy():
    print("=" * 80)
    print(f"DEPLOYING 9:16 MOBILE HERO VIDEO TO LIVE THEME: {THEME_ID}")
    print("=" * 80)

    # 1. sections/slideshow.liquid
    slideshow_path = os.path.join(PROJECT_ROOT, "theme", "sections", "slideshow.liquid")
    with open(slideshow_path, "r", encoding="utf-8") as f:
        slideshow_content = f.read()

    # 2. templates/index.json
    index_path = os.path.join(PROJECT_ROOT, "theme", "templates", "index.json")
    with open(index_path, "r", encoding="utf-8") as f:
        index_content = f.read()

    # 3. snippets/media.liquid
    media_path = os.path.join(PROJECT_ROOT, "theme", "snippets", "media.liquid")
    with open(media_path, "r", encoding="utf-8") as f:
        media_content = f.read()

    payload = [
        {
            "filename": "sections/slideshow.liquid",
            "body": {
                "type": "TEXT",
                "value": slideshow_content
            }
        },
        {
            "filename": "templates/index.json",
            "body": {
                "type": "TEXT",
                "value": index_content
            }
        },
        {
            "filename": "snippets/media.liquid",
            "body": {
                "type": "TEXT",
                "value": media_content
            }
        }
    ]

    print("Deploying sections/slideshow.liquid and templates/index.json...")
    data, ext, err = execute_shopify_graphql(
        THEME_FILES_MUTATION,
        variables={"files": payload, "themeId": THEME_ID}
    )

    if err or not data:
        print(f"GraphQL execution error: {err}")
        sys.exit(1)

    result = data.get("themeFilesUpsert", {})
    user_errors = result.get("userErrors", [])
    if user_errors:
        print(f"User errors: {user_errors}")
        sys.exit(1)

    upserted = result.get("upsertedThemeFiles", [])
    print(f"Successfully upserted: {[u['filename'] for u in upserted]}")

    # Optional: Deploy binary video asset
    video_asset_path = os.path.join(PROJECT_ROOT, "theme", "assets", "hero-video-mobile-9-16.mp4")
    if os.path.exists(video_asset_path):
        print(f"\nUploading theme asset hero-video-mobile-9-16.mp4 ({os.path.getsize(video_asset_path)} bytes)...")
        with open(video_asset_path, "rb") as vf:
            video_b64 = base64.b64encode(vf.read()).decode("utf-8")
        
        asset_payload = [{
            "filename": "assets/hero-video-mobile-9-16.mp4",
            "body": {
                "type": "BASE64",
                "value": video_b64
            }
        }]

        v_data, v_ext, v_err = execute_shopify_graphql(
            THEME_FILES_MUTATION,
            variables={"files": asset_payload, "themeId": THEME_ID}
        )
        if v_data and "themeFilesUpsert" in v_data:
            v_res = v_data["themeFilesUpsert"]
            if not v_res.get("userErrors"):
                print(f"Successfully uploaded binary asset: {[u['filename'] for u in v_res.get('upsertedThemeFiles', [])]}")
            else:
                print(f"Asset upload note (non-critical, Shopify CDN is primary): {v_res.get('userErrors')}")
        else:
            print(f"Asset upload error (non-critical): {v_err}")

    print("=" * 80)
    print("DEPLOYMENT COMPLETE!")
    print("=" * 80)

if __name__ == "__main__":
    deploy()
