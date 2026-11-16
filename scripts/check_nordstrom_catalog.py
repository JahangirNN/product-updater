import os
import glob
import json
from collections import Counter

PROJECT_ROOT = "product-updater"
import sys
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_taxonomy import resolve_product_type, resolve_authentic_vendor

files = glob.glob(os.path.join(PROJECT_ROOT, "storage", "db", "nordstrom", "products", "*.json"))
types = Counter()
vendors = Counter()

for f in files:
    with open(f, "r", encoding="utf-8") as fp:
        d = json.load(fp)
    ptype = resolve_product_type(d)
    vendor = resolve_authentic_vendor(d)
    types[ptype] += 1
    vendors[vendor] += 1

print("Nordstrom Product Types:")
for t, c in types.most_common():
    print(f"  {t:30s}: {c}")

print("\nNordstrom Vendors:")
for v, c in vendors.most_common():
    print(f"  {v:30s}: {c}")
