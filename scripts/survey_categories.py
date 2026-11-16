import os
import glob
import json
from collections import Counter

PROJECT_ROOT = "product-updater"
pattern = os.path.join(PROJECT_ROOT, "storage", "db", "**", "products", "*.json")
files = glob.glob(pattern, recursive=True)

store_counts = Counter()
product_type_counts = Counter()
vendor_counts = Counter()
store_type_pairs = Counter()

for f in files:
    try:
        with open(f, "r", encoding="utf-8") as fp:
            d = json.load(fp)
        store = (d.get("source_store") or d.get("store") or "unknown").lower()
        ptype = d.get("product_type") or d.get("productType") or d.get("category") or "Unknown"
        vendor = d.get("vendor") or d.get("brand") or "Unknown"
        
        store_counts[store] += 1
        product_type_counts[ptype] += 1
        vendor_counts[vendor] += 1
        store_type_pairs[(store, ptype)] += 1
    except Exception:
        pass

print("=== STORES ===")
for st, cnt in store_counts.most_common():
    print(f"  {st:20s}: {cnt:5d} products")

print("\n=== TOP PRODUCT TYPES / CATEGORIES ===")
for pt, cnt in product_type_counts.most_common(30):
    print(f"  {pt:35s}: {cnt:5d} products")

print("\n=== STORE + PRODUCT TYPE PAIRS ===")
for (st, pt), cnt in store_type_pairs.most_common(40):
    print(f"  {st:15s} | {pt:30s}: {cnt:5d} products")
