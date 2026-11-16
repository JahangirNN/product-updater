import os
import sys
import json
import glob

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
zero_json = os.path.join(PROJECT_ROOT, "storage", "zero_image_products.json")

with open(zero_json, "r", encoding="utf-8") as f:
    data = json.load(f)

products = data.get("products", [])
print(f"Total zero-image products: {len(products)}")

# Build lookup by shopify_product_id or handle
all_db_files = glob.glob(os.path.join(PROJECT_ROOT, "storage", "db", "**", "products", "*.json"), recursive=True)
print(f"Total DB files scanned: {len(all_db_files)}")

db_by_gid = {}
db_by_handle = {}
for fp in all_db_files:
    try:
        with open(fp, "r", encoding="utf-8") as f:
            d = json.load(f)
        gid = d.get("shopify_product_id")
        handle = d.get("handle")
        if gid:
            db_by_gid[gid] = (fp, d)
        if handle:
            db_by_handle[handle] = (fp, d)
    except Exception:
        pass

found_in_db = 0
missing_in_db = 0

report = []
for p in products:
    gid = p["id"]
    handle = p["handle"]
    
    match = db_by_gid.get(gid) or db_by_handle.get(handle)
    if match:
        found_in_db += 1
        fp, d = match
        images = d.get("images", [])
        primary = d.get("primary_image")
        source_url = d.get("source_url") or d.get("url") or d.get("link")
        report.append({
            "id": gid,
            "title": p["title"],
            "handle": handle,
            "vendor": p["vendor"],
            "productType": p["productType"],
            "store": d.get("source_store") or d.get("store"),
            "source_url": source_url,
            "db_image_count": len(images),
            "sample_images": images[:3],
            "file": fp
        })
    else:
        missing_in_db += 1
        report.append({
            "id": gid,
            "title": p["title"],
            "handle": handle,
            "vendor": p["vendor"],
            "productType": p["productType"],
            "store": None,
            "source_url": None,
            "db_image_count": 0,
            "sample_images": [],
            "file": None
        })

print(f"Found in local DB: {found_in_db} / {len(products)}")
print(f"Missing in local DB: {missing_in_db} / {len(products)}")

# Breakdown by store
by_store = {}
for r in report:
    st = r["store"] or "Unknown"
    by_store[st] = by_store.get(st, 0) + 1
print("Store breakdown:", by_store)

with open(os.path.join(PROJECT_ROOT, "storage", "zero_image_audit_detail.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)

print("Saved detailed report to product-updater/storage/zero_image_audit_detail.json")
