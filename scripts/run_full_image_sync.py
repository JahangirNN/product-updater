"""
Full Image Scraping, Verification, DB Update, and Shopify Sync Pipeline
For all 47 zero-image products across Jomashop, JW PEI, and Sephora.
"""
import sys
import os
import json
import base64
import time
from datetime import datetime, timezone
import requests

PROJECT_ROOT = "product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import get_shopify_credentials, get_shopify_http_client, execute_shopify_graphql

AUDIT_FILE = "product-updater/storage/zero_image_audit_detail.json"
MANIFEST_FILE = "product-updater/storage/verified_images_manifest.json"

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

DELETE_MEDIA_MUTATION = """
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

JOMA_WATCH_QUERY = """
query getWatchMedia($urlKey: String!) {
  products(filter: { url_key: { eq: $urlKey } }) {
    items {
      id
      sku
      name
      url_key
      stock_status
      image {
        url_nocache
      }
      media_gallery {
        ... on ProductImage {
          url_nocache
        }
      }
    }
  }
}
"""

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
}

IMAGE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
}


def verify_and_download_image(url: str, min_bytes: int = 5000):
    """
    Downloads image and verifies status 200, Content-Type is image, length >= min_bytes.
    Returns (success, content_bytes, content_type).
    """
    try:
        r = requests.get(url, headers=IMAGE_HEADERS, timeout=15)
        if r.status_code == 200:
            ctype = r.headers.get("Content-Type", "").lower()
            clength = len(r.content)
            is_img = "image" in ctype or url.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
            if is_img and clength >= min_bytes:
                return True, r.content, ctype
        return False, None, f"Status: {r.status_code}, Size: {len(r.content) if r.content else 0}"
    except Exception as e:
        return False, None, str(e)


def scrape_jomashop_images(handle: str):
    """Scrape authentic images via Jomashop GraphQL."""
    candidate_urls = []
    try:
        resp = requests.post(
            "https://www.jomashop.com/graphql",
            json={"query": JOMA_WATCH_QUERY, "variables": {"urlKey": handle}},
            headers={
                "User-Agent": BROWSER_HEADERS["User-Agent"],
                "Content-Type": "application/json",
                "Accept": "*/*"
            },
            timeout=15
        )
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("data", {}).get("products", {}).get("items", [])
            if items:
                p = items[0]
                if p.get("image", {}).get("url_nocache"):
                    candidate_urls.append(p["image"]["url_nocache"])
                for mg in p.get("media_gallery", []):
                    u = mg.get("url_nocache")
                    if u and u not in candidate_urls:
                        candidate_urls.append(u)
    except Exception as e:
        print(f"  [ERROR] Jomashop scraping error for {handle}: {e}")
    return candidate_urls


def scrape_jwpei_images(source_url: str, local_images: list):
    """Scrape authentic images via JW PEI .js endpoint."""
    handle = source_url.rstrip("/").split("/")[-1].split("?")[0]
    candidate_urls = []
    try:
        js_url = f"https://www.jwpei.com/products/{handle}.js"
        resp = requests.get(js_url, headers=BROWSER_HEADERS, timeout=12)
        if resp.status_code == 200:
            js_data = resp.json()
            for u in js_data.get("images", []):
                if u.startswith("//"):
                    u = "https:" + u
                elif not u.startswith("http"):
                    u = "https://" + u
                if u not in candidate_urls:
                    candidate_urls.append(u)
    except Exception as e:
        print(f"  [WARN] JW PEI .js fetch error for {handle}: {e}")

    # Fallback / merge with local images if any
    for u in local_images:
        if u and u not in candidate_urls:
            candidate_urls.append(u)
            
    return candidate_urls


def upload_images_to_shopify(client, domain: str, token: str, gid: str, image_items: list, max_images: int = 4):
    """
    Uploads verified image bytes as base64 attachments to Shopify REST endpoint.
    image_items is a list of tuples: (url, bytes).
    """
    num_id = gid.split("/")[-1]
    uploaded = 0

    for idx, (img_url, img_bytes) in enumerate(image_items[:max_images]):
        b64_str = base64.b64encode(img_bytes).decode("utf-8")
        ext = "jpg"
        if ".png" in img_url.lower():
            ext = "png"
        elif ".webp" in img_url.lower():
            ext = "webp"

        filename = f"prod-{num_id}-{idx+1}.{ext}"
        rest_url = f"https://{domain}/admin/api/2024-01/products/{num_id}/images.json"

        # Retry with exponential backoff on 429
        for attempt in range(5):
            try:
                resp = client.post(
                    rest_url,
                    json={"image": {"attachment": b64_str, "filename": filename}},
                    headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"},
                    timeout=30
                )
                if resp.status_code in (200, 201):
                    uploaded += 1
                    break
                elif resp.status_code == 429:
                    wait_sec = 2.0 * (attempt + 1)
                    print(f"    [RATE LIMIT] 429 received, backing off {wait_sec}s...")
                    time.sleep(wait_sec)
                else:
                    print(f"    [WARN] Upload failed for #{idx+1}: {resp.status_code} - {resp.text[:100]}")
                    break
            except Exception as ex:
                print(f"    [ERROR] Network error during upload attempt {attempt}: {ex}")
                time.sleep(2.0)

        time.sleep(0.35)

    # Clean up any FAILED media
    try:
        data, _, _ = execute_shopify_graphql(CHECK_MEDIA_QUERY, variables={"id": gid})
        nodes = data.get("product", {}).get("media", {}).get("nodes", []) if data else []
        failed_ids = [m["id"] for m in nodes if m.get("status") == "FAILED"]
        if failed_ids:
            print(f"    [CLEANUP] Removing {len(failed_ids)} FAILED media nodes for {num_id}")
            execute_shopify_graphql(DELETE_MEDIA_MUTATION, variables={"productId": gid, "mediaIds": failed_ids})
    except Exception as ex:
        print(f"    [WARN] Cleanup query failed: {ex}")

    return uploaded


def run_pipeline():
    print("=" * 70)
    print("STARTING FULL IMAGE SCRAPING, VERIFICATION & SHOPIFY SYNC PIPELINE")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    domain, token, _ = get_shopify_credentials()
    client = get_shopify_http_client()

    with open(AUDIT_FILE, "r", encoding="utf-8") as f:
        audit_items = json.load(f)

    print(f"Loaded {len(audit_items)} target products from {AUDIT_FILE}")

    manifest_entries = []
    total_images_verified = 0
    total_images_uploaded = 0

    for idx, item in enumerate(audit_items):
        gid = item["id"]
        store = item["store"]
        title = item["title"]
        handle = item["handle"]
        fpath = item["file"]
        source_url = item.get("source_url", "")

        print(f"\n[{idx+1}/{len(audit_items)}] Processing {store.upper()}: '{title[:40]}' ({gid})")

        # 1. Collect candidate image URLs
        local_data = {}
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as lf:
                local_data = json.load(lf)

        candidates = []
        if store == "jomashop":
            candidates = scrape_jomashop_images(handle)
        elif store == "jwpei":
            local_imgs = local_data.get("images", [])
            candidates = scrape_jwpei_images(source_url, local_imgs)
        elif store == "sephora":
            candidates = list(local_data.get("images", []))
            if local_data.get("primary_image_url") and local_data["primary_image_url"] not in candidates:
                candidates.insert(0, local_data["primary_image_url"])

        print(f"  Candidate image URLs found: {len(candidates)}")

        # 2. Verify all images (HTTP 200, Content-Type image, size >= 5000 bytes)
        verified_images = []  # list of (url, bytes)
        for u in candidates:
            ok, bts, msg = verify_and_download_image(u, min_bytes=5000)
            if ok:
                verified_images.append((u, bts))
            else:
                print(f"    Rejected image {u}: {msg}")

        verified_urls = [u for u, _ in verified_images]
        print(f"  Verified authentic images: {len(verified_urls)}")
        total_images_verified += len(verified_urls)

        if not verified_urls:
            print(f"  [CRITICAL ERROR] 0 verified images for product {gid}!")
            manifest_entries.append({
                "shopify_id": gid,
                "store": store,
                "title": title,
                "handle": handle,
                "verified_images_count": 0,
                "uploaded_to_shopify": 0,
                "shopify_media_count": 0,
                "status": "FAILED_VERIFICATION"
            })
            continue

        # 3. Update Local Database
        if os.path.exists(fpath):
            local_data["images"] = verified_urls
            local_data["primary_image"] = verified_urls[0]
            if store == "sephora":
                local_data["primary_image_url"] = verified_urls[0]
                local_data["shopify_image_synced"] = True
            elif store == "jwpei":
                local_data["image"] = verified_urls[0]
                local_data["image_url"] = verified_urls[0]
            
            local_data["last_verified_at"] = datetime.now(timezone.utc).isoformat()
            local_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            local_data["shopify_sync_pending"] = False

            with open(fpath, "w", encoding="utf-8") as lf:
                json.dump(local_data, lf, indent=2, ensure_ascii=False)
            print(f"  Updated local DB file: {os.path.basename(fpath)}")

        # 4. Check existing media on Shopify before uploading (e.g. if already uploaded during tests)
        media_count_before = 0
        try:
            m_data, _, _ = execute_shopify_graphql(CHECK_MEDIA_QUERY, variables={"id": gid})
            p_node = m_data.get("product") or {}
            m_nodes = p_node.get("media", {}).get("nodes", [])
            ready_nodes = [m for m in m_nodes if m.get("status") == "READY"]
            media_count_before = len(ready_nodes)
        except Exception:
            pass

        uploaded_count = 0
        if media_count_before >= 3:
            print(f"  Product already has {media_count_before} READY media nodes on Shopify.")
            uploaded_count = media_count_before
        else:
            # Upload top 3-4 verified images to Shopify
            upload_target = verified_images[:4]
            uploaded_count = upload_images_to_shopify(client, domain, token, gid, upload_target, max_images=4)
            print(f"  Uploaded {uploaded_count} images to Shopify.")
            total_images_uploaded += uploaded_count

        # 5. Verify Live Shopify Media
        time.sleep(1.0)
        final_media_count = 0
        shopify_status = "UNKNOWN"
        shopify_inventory = 0
        media_details = []

        try:
            m_data, _, _ = execute_shopify_graphql(CHECK_MEDIA_QUERY, variables={"id": gid})
            p_node = m_data.get("product") or {}
            shopify_status = p_node.get("status", "UNKNOWN")
            shopify_inventory = p_node.get("totalInventory", 0)
            m_nodes = p_node.get("media", {}).get("nodes", [])
            ready_nodes = [m for m in m_nodes if m.get("status") == "READY"]
            final_media_count = len(ready_nodes)
            media_details = [{"id": m["id"], "status": m["status"]} for m in m_nodes]
        except Exception as e:
            print(f"  [ERROR] Final media check failed for {gid}: {e}")

        print(f"  Live Shopify Verification -> Media Count: {final_media_count}, Status: {shopify_status}, Total Inventory: {shopify_inventory}")

        manifest_entries.append({
            "shopify_id": gid,
            "store": store,
            "title": title,
            "handle": handle,
            "verified_images_count": len(verified_urls),
            "verified_sample_url": verified_urls[0],
            "uploaded_count": uploaded_count,
            "shopify_media_count": final_media_count,
            "shopify_status": shopify_status,
            "shopify_inventory": shopify_inventory,
            "media_nodes": media_details,
            "verified_at": datetime.now(timezone.utc).isoformat()
        })

    # Summary
    zero_media_final = [m for m in manifest_entries if m["shopify_media_count"] == 0]

    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_products_target": len(audit_items),
        "total_products_verified": len([m for m in manifest_entries if m["verified_images_count"] > 0]),
        "total_images_verified": total_images_verified,
        "total_images_uploaded": total_images_uploaded,
        "zero_media_remaining_count": len(zero_media_final),
        "zero_media_remaining": zero_media_final,
        "store_breakdown": {
            "jomashop": {
                "products": len([m for m in manifest_entries if m["store"] == "jomashop"]),
                "verified_images": sum(m["verified_images_count"] for m in manifest_entries if m["store"] == "jomashop"),
                "media_attached": sum(m["shopify_media_count"] for m in manifest_entries if m["store"] == "jomashop")
            },
            "jwpei": {
                "products": len([m for m in manifest_entries if m["store"] == "jwpei"]),
                "verified_images": sum(m["verified_images_count"] for m in manifest_entries if m["store"] == "jwpei"),
                "media_attached": sum(m["shopify_media_count"] for m in manifest_entries if m["store"] == "jwpei")
            },
            "sephora": {
                "products": len([m for m in manifest_entries if m["store"] == "sephora"]),
                "verified_images": sum(m["verified_images_count"] for m in manifest_entries if m["store"] == "sephora"),
                "media_attached": sum(m["shopify_media_count"] for m in manifest_entries if m["store"] == "sephora")
            }
        },
        "products": manifest_entries
    }

    with open(MANIFEST_FILE, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print("PIPELINE EXECUTION COMPLETED")
    print(f"Total Products: {len(audit_items)}")
    print(f"Verified with Authentic Images: {manifest['total_products_verified']}/{len(audit_items)}")
    print(f"Zero Media Remaining on Shopify: {len(zero_media_final)}")
    print(f"Summary Manifest written to: {MANIFEST_FILE}")
    print("=" * 70)

    return manifest


if __name__ == "__main__":
    run_pipeline()
