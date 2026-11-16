"""
Independent Post-Sync Verification Script
Verifies:
1. All 47 products on Shopify have media attached (0 remain with 0 images).
2. All local DB files in product-updater/storage/db/<store>/products/<id>.json
   contain non-empty 'images' and 'primary_image'.
"""
import sys
import os
import json

PROJECT_ROOT = "product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

CHECK_MEDIA_QUERY = """
query getProductMedia($id: ID!) {
  product(id: $id) {
    id
    title
    status
    totalInventory
    media(first: 10) {
      nodes {
        id
        status
        mediaContentType
      }
    }
  }
}
"""

with open("product-updater/storage/zero_image_audit_detail.json", "r", encoding="utf-8") as f:
    target_products = json.load(f)

print(f"Auditing all {len(target_products)} target products against live Shopify...")

zero_image_shopify = []
local_missing_images = []
media_counts = {}

for idx, p in enumerate(target_products):
    gid = p["id"]
    title = p["title"]
    store = p["store"]
    fpath = p["file"]

    # 1. Live Shopify check
    res, errs, _ = execute_shopify_graphql(CHECK_MEDIA_QUERY, variables={"id": gid})
    prod_node = res.get("product") or {}
    media_nodes = prod_node.get("media", {}).get("nodes", [])
    ready_media = [m for m in media_nodes if m.get("status") == "READY"]

    count = len(ready_media)
    media_counts[gid] = count
    if count == 0:
        zero_image_shopify.append({"id": gid, "title": title, "store": store})

    # 2. Local DB check
    if not os.path.exists(fpath):
        local_missing_images.append({"id": gid, "file": fpath, "reason": "file_not_found"})
    else:
        with open(fpath, "r", encoding="utf-8") as lf:
            ld = json.load(lf)
            imgs = ld.get("images", [])
            primary = ld.get("primary_image") or ld.get("primary_image_url") or ld.get("image")
            if not imgs or not primary:
                local_missing_images.append({"id": gid, "file": fpath, "imgs_len": len(imgs), "primary": primary})

    sys.stdout.write(f"\rChecked {idx+1}/{len(target_products)}: {store.upper()} '{title[:30]}' -> {count} Shopify media")
    sys.stdout.flush()

print("\n\n" + "=" * 60)
print("AUDIT RESULTS SUMMARY:")
print("=" * 60)
print(f"Total Target Products: {len(target_products)}")
print(f"Products with >= 1 Media on Shopify: {len(target_products) - len(zero_image_shopify)} / {len(target_products)}")
print(f"Products with 0 Media on Shopify: {len(zero_image_shopify)}")
print(f"Products with local DB updated: {len(target_products) - len(local_missing_images)} / {len(target_products)}")
print(f"Total Shopify Media attached across all 47 products: {sum(media_counts.values())}")

if zero_image_shopify:
    print("\nFAILURES on Shopify:")
    for f in zero_image_shopify:
        print(f"  - {f['id']} ({f['store']}): {f['title']}")
else:
    print("\nSUCCESS: 0 products remain without images on Shopify! 100% verified!")

if local_missing_images:
    print("\nFAILURES in Local DB:")
    for f in local_missing_images:
        print(f"  - {f}")
else:
    print("SUCCESS: 100% of local database files have verified images and primary_image!")
print("=" * 60)
