import os
import sys
import json
import httpx

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from storage.shopify_auth import get_shopify_credentials

domain, token, version = get_shopify_credentials()
headers = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": token
}

# Nike collection ID: gid://shopify/Collection/693162475686 -> 693162475686
col_id = 693162475686

# Try Method 1: PUT /admin/api/2024-07/smart_collections/{col_id}.json with published: true
url1 = f"https://{domain}/admin/api/2024-07/smart_collections/{col_id}.json"
payload1 = {
    "smart_collection": {
        "id": col_id,
        "published": True
    }
}
r1 = httpx.put(url1, json=payload1, headers=headers)
print("Method 1 (PUT smart_collection):", r1.status_code, r1.text[:300])

# Try Method 2: POST /admin/api/2024-07/publications/328164671654/collection_publications.json
pub_id = 328164671654
url2 = f"https://{domain}/admin/api/2024-07/publications/{pub_id}/collection_publications.json"
payload2 = {
    "collection_publication": {
        "collection_id": col_id
    }
}
r2 = httpx.post(url2, json=payload2, headers=headers)
print("Method 2 (POST collection_publications):", r2.status_code, r2.text[:300])

# Check storefront status
store_res = httpx.get("https://therareavenue.com/collections/nike", follow_redirects=True)
print("Storefront status for /collections/nike:", store_res.status_code)
