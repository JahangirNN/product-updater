import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import httpx
from storage.shopify_auth import get_shopify_credentials

domain, token, version = get_shopify_credentials()
coach_id = 15841760772262 # Pouch In Signature Canvas

url = f"https://{domain}/admin/api/{version}/products/{coach_id}.json"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}

# Try PUT with published: true
payload = {
    "product": {
        "id": coach_id,
        "published": True
    }
}

resp = httpx.put(url, json=payload, headers=headers)
print("PUT Status:", resp.status_code)
print("PUT Response:", resp.text[:500])

if resp.status_code == 200:
    # Now check storefront URL
    sr = httpx.get("https://therareavenue.com/products/pouch-in-signature-canvas", follow_redirects=True)
    print("Storefront Status after REST publish:", sr.status_code)
