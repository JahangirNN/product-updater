import sys
import base64
import requests

PROJECT_ROOT = "product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import get_shopify_credentials, get_shopify_http_client

def test_image_upload():
    # 1. Download image from Sephora using browser User-Agent
    img_url = "https://www.sephora.com/productimages/sku/s2636744-main-zoom.jpg"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    resp = requests.get(img_url, headers=headers)
    print("Sephora download status:", resp.status_code, "Length:", len(resp.content))
    if resp.status_code != 200:
        return

    b64_data = base64.b64encode(resp.content).decode("utf-8")

    # 2. Upload to Shopify via REST images.json
    domain, token, _ = get_shopify_credentials()
    client = get_shopify_http_client()
    prod_id = "15993205489830"
    url = f"https://{domain}/admin/api/2024-01/products/{prod_id}/images.json"
    
    payload = {
        "image": {
            "attachment": b64_data,
            "filename": "milky-oil-makeup-remover.jpg"
        }
    }
    
    res = client.post(url, json=payload, headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"})
    print("Shopify upload status:", res.status_code)
    try:
        print("Response:", res.json())
    except Exception as e:
        print("Response text:", res.text)

if __name__ == "__main__":
    test_image_upload()
