import sys
import httpx
sys.path.insert(0, "product-updater")
from storage.shopify_auth import get_shopify_credentials

domain, token, version = get_shopify_credentials()
print(f"Testing REST API on {domain}...")

headers = {
    "X-Shopify-Access-Token": token,
    "Content-Type": "application/json"
}

url = f"https://{domain}/admin/api/2024-01/products/15993205981350.json"
payload = {
    "product": {
        "id": 15993205981350,
        "published": True
    }
}

resp = httpx.put(url, json=payload, headers=headers)
print("Status code:", resp.status_code)
print("Response text:", resp.text[:500])
