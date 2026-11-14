import os
import sys
import json
import time
import httpx

PROJECT_ROOT = "product-updater"
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import get_shopify_credentials

PILOT_FILES = [
    "00746b4ef0f45103.json",
    "0263b15b38529dfe.json",
    "026b5e220a9f4985.json",
    "028a15e63b2cb6f9.json",
    "034159e1dcfe57b9.json",
    "04c4dd45f575ba41.json",
    "050a2d8ca25205a5.json",
    "05266852db888a70.json",
    "05824dadb0d3488f.json",
    "064cffc5d3a5b0a4.json",
    "0749eca097bf76c1.json",
    "08702e1da9320ab5.json",
    "09fb3e7f2425a515.json",
    "14f3a9acb4683314.json"
]

def publish_all_pilot_products():
    domain, token, _ = get_shopify_credentials()
    headers = {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json"
    }
    
    print(f"Publishing {len(PILOT_FILES)} pilot products to Online Store via REST API...")
    success_count = 0
    for fn in PILOT_FILES:
        fp = os.path.join(PROJECT_ROOT, "storage", "db", "sephora", "products", fn)
        with open(fp, "r", encoding="utf-8") as f:
            p = json.load(f)
            gid = p.get("shopify_product_id")
            title = p.get("title", "")
            brand = p.get("brand", "")

        if not gid:
            print(f"  [SKIP] No shopify_product_id for {title}")
            continue

        num_id = gid.split("/")[-1]
        url = f"https://{domain}/admin/api/2024-01/products/{num_id}.json"
        payload = {
            "product": {
                "id": int(num_id),
                "published": True,
                "status": "active"
            }
        }
        
        try:
            resp = httpx.put(url, json=payload, headers=headers, timeout=15.0)
            if resp.status_code == 200:
                print(f"  [PUBLISHED] [{brand}] {title[:40]} (ID: {num_id})")
                success_count += 1
            else:
                print(f"  [ERROR {resp.status_code}] {title[:40]}: {resp.text[:100]}")
        except Exception as e:
            print(f"  [EXCEPTION] {title[:40]}: {e}")
        time.sleep(0.5)

    print(f"\nSuccessfully published {success_count}/{len(PILOT_FILES)} pilot products to Online Store!")

if __name__ == "__main__":
    publish_all_pilot_products()
