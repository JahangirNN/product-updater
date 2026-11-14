"""
Bulk Image Ingestion & CDN Hosting Pipeline for Sephora Beauty Catalog
Downloads high-res product & swatch imagery from Sephora CDN with authenticated browser headers,
uploads directly to Shopify via REST base64 attachments (generating permanent cdn.shopify.com assets),
and purges any FAILED media nodes.
"""
import os
import sys
import json
import time
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

PROJECT_ROOT = "product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import get_shopify_credentials, get_shopify_http_client, execute_shopify_graphql

CHECK_FAILED_MEDIA_QUERY = """
query getProductFailedMedia($id: ID!) {
  product(id: $id) {
    media(first: 25) {
      nodes {
        id
        status
      }
    }
  }
}
"""

PURGE_MEDIA_MUTATION = """
mutation productDeleteMedia($productId: ID!, $mediaIds: [ID!]!) {
  productDeleteMedia(productId: $productId, mediaIds: $mediaIds) {
    deletedMediaIds
    userErrors {
      field
      message
    }
  }
}
"""

def process_single_product_images(file_path: str, domain: str, token: str) -> bool:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            p_data = json.load(f)

        gid = p_data.get("shopify_product_id")
        if not gid:
            return False

        if p_data.get("shopify_image_synced"):
            return True

        num_id = gid.split("/")[-1]
        images = p_data.get("images", [])
        if not images:
            p_data["shopify_image_synced"] = True
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(p_data, f, indent=2, ensure_ascii=False)
            return True

        session = requests.Session()
        ua_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # Upload primary and up to 3 gallery images (max 4 total per product for high visual fidelity & speed)
        uploaded = 0
        for idx, img_url in enumerate(images[:4]):
            try:
                r = session.get(img_url, headers=ua_headers, timeout=12)
                if r.status_code != 200 or len(r.content) < 500:
                    continue

                b64_str = base64.b64encode(r.content).decode("utf-8")
                ext = "jpg"
                if ".png" in img_url.lower():
                    ext = "png"
                elif ".webp" in img_url.lower():
                    ext = "webp"

                filename = f"prod-{num_id}-{idx+1}.{ext}"
                rest_url = f"https://{domain}/admin/api/2024-01/products/{num_id}/images.json"

                resp = session.post(
                    rest_url,
                    json={"image": {"attachment": b64_str, "filename": filename}},
                    headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"},
                    timeout=18
                )

                if resp.status_code in (200, 201):
                    uploaded += 1
                elif resp.status_code == 429:
                    time.sleep(2.0)

                time.sleep(0.3)
            except Exception:
                pass

        # Cleanup any FAILED media nodes left over from initial GraphQL ingestion
        try:
            data, _, _ = execute_shopify_graphql(CHECK_FAILED_MEDIA_QUERY, variables={"id": gid})
            nodes = data.get("product", {}).get("media", {}).get("nodes", []) if data else []
            failed_ids = [m["id"] for m in nodes if m.get("status") == "FAILED"]
            if failed_ids:
                execute_shopify_graphql(PURGE_MEDIA_MUTATION, variables={"productId": gid, "mediaIds": failed_ids})
        except Exception:
            pass

        p_data["shopify_image_synced"] = True
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(p_data, f, indent=2, ensure_ascii=False)

        return uploaded > 0
    except Exception as e:
        return False

def sync_all_catalog_images():
    print("=" * 80)
    print("STARTING BULK BEAUTY IMAGE SYNC (SEPHORA -> SHOPIFY CDN)")
    print("=" * 80)

    domain, token, _ = get_shopify_credentials()
    p_dir = os.path.join(PROJECT_ROOT, "storage", "db", "sephora", "products")
    files = [os.path.join(p_dir, fn) for fn in os.listdir(p_dir) if fn.endswith(".json")]

    synced_count = 0
    skipped_count = 0
    failed_count = 0

    to_process = []
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                d = json.load(f)
            if d.get("shopify_product_id") and not d.get("shopify_image_synced"):
                to_process.append(fp)
            elif d.get("shopify_image_synced"):
                skipped_count += 1
        except Exception:
            pass

    total = len(to_process)
    print(f"Products ready for image upload: {total} (Already completed: {skipped_count})")

    # Use ThreadPoolExecutor with 3 workers for steady, rate-limit friendly ingestion
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(process_single_product_images, fp, domain, token): fp for fp in to_process}
        for idx, future in enumerate(as_completed(futures), 1):
            fp = futures[future]
            try:
                res = future.result()
                if res:
                    synced_count += 1
                else:
                    failed_count += 1
            except Exception:
                failed_count += 1

            if idx % 10 == 0 or idx == total:
                print(f"[{idx}/{total}] Images Synced: {synced_count} | Failed: {failed_count}")

    print("=" * 80)
    print(f"IMAGE SYNC COMPLETE: {synced_count} products updated on Shopify CDN.")
    print("=" * 80)

if __name__ == "__main__":
    sync_all_catalog_images()
