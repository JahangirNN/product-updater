import os
import json

p_dir = "product-updater/storage/db/sephora/products"
files = [fn for fn in os.listdir(p_dir) if fn.endswith(".json")]
print(f"Total Sephora products in local database: {len(files)}")

synced = 0
not_synced = 0
brands = {}
for fn in files:
    with open(os.path.join(p_dir, fn), encoding="utf-8") as f:
        p = json.load(f)
        b = p.get("brand") or p.get("vendor") or "Unknown"
        brands[b] = brands.get(b, 0) + 1
        if p.get("shopify_product_id"):
            synced += 1
        else:
            not_synced += 1

print(f"Already synced: {synced}")
print(f"Pending sync: {not_synced}")
print("\nProduct count by brand:")
for b, count in sorted(brands.items(), key=lambda x: -x[1]):
    print(f"  - {b}: {count} products")
