import os
import sys
import json
import time
import base64
import requests

PROJECT_ROOT = "product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import get_shopify_credentials, get_shopify_http_client, execute_shopify_graphql

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

CHECK_MEDIA_QUERY = """
query getProductMedia($id: ID!) {
  product(id: $id) {
    media(first: 20) {
      nodes {
        id
        status
        mediaContentType
      }
    }
  }
}
"""

def sync_product_images(p_data: dict, domain: str, token: str, client: requests.Session, max_images: int = 4) -> bool:
    gid = p_data.get("shopify_product_id")
    if not gid:
        return False
        
    num_id = gid.split("/")[-1]
    images = p_data.get("images", [])
    if not images:
        return True

    # 1. Download and upload images
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    uploaded_count = 0
    for idx, img_url in enumerate(images[:max_images]):
        try:
            r = requests.get(img_url, headers=headers, timeout=10)
            if r.status_code != 200 or len(r.content) < 1000:
                continue
            
            b64_str = base64.b64encode(r.content).decode("utf-8")
            ext = "jpg"
            if ".png" in img_url.lower():
                ext = "png"
            elif ".webp" in img_url.lower():
                ext = "webp"
                
            filename = f"prod-{num_id}-{idx+1}.{ext}"
            rest_url = f"https://{domain}/admin/api/2024-01/products/{num_id}/images.json"
            
            resp = client.post(
                rest_url,
                json={"image": {"attachment": b64_str, "filename": filename}},
                headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"},
                timeout=15
            )
            
            if resp.status_code in (200, 201):
                uploaded_count += 1
            elif resp.status_code == 429:
                time.sleep(2.0)
            
            time.sleep(0.3)
        except Exception as e:
            pass

    # 2. Cleanup any FAILED media
    try:
        data, _, _ = execute_shopify_graphql(CHECK_MEDIA_QUERY, variables={"id": gid})
        nodes = data.get("product", {}).get("media", {}).get("nodes", []) if data else []
        failed_ids = [m["id"] for m in nodes if m.get("status") == "FAILED"]
        if failed_ids:
            execute_shopify_graphql(DELETE_MEDIA_MUTATION, variables={"productId": gid, "mediaIds": failed_ids})
    except Exception:
        pass

    return uploaded_count > 0

if __name__ == "__main__":
    domain, token, _ = get_shopify_credentials()
    client = get_shopify_http_client()
    
    # Test on Saie Dew Blush
    p_dir = os.path.join(PROJECT_ROOT, "storage", "db", "sephora", "products")
    # find dew blush
    for fn in os.listdir(p_dir):
        fp = os.path.join(p_dir, fn)
        with open(fp, "r", encoding="utf-8") as f:
            d = json.load(f)
        if "dew blush" in d.get("title", "").lower() and d.get("shopify_product_id"):
            print("Testing on:", d.get("title"), d.get("shopify_product_id"))
            ok = sync_product_images(d, domain, token, client, max_images=3)
            print("Sync result:", ok)
            break
