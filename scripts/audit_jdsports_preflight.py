import os
import glob
import json
from collections import Counter

files = glob.glob("storage/db/jdsports/products/*.json")
print(f"Total JD Sports files: {len(files)}")

types = Counter()
vendors = Counter()
availability = Counter()
genders = Counter()
option_names = Counter()
missing_imgs = 0
broken_imgs = 0
unicode_issues = 0
zero_prices = 0

for f in files:
    with open(f, "r", encoding="utf-8") as fp:
        raw_text = fp.read()
        if "\ufffd" in raw_text or "\\ufffd" in raw_text:
            unicode_issues += 1
        d = json.loads(raw_text)

    types[d.get("product_type", "Unknown")] += 1
    vendors[d.get("vendor", "Unknown")] += 1
    availability[d.get("availability", "Unknown")] += 1
    genders[d.get("gender", "Unknown")] += 1

    price = float(d.get("source_price") or d.get("price_current") or 0.0)
    if price <= 0:
        zero_prices += 1

    imgs = d.get("images", [])
    if not imgs and not d.get("image") and not d.get("image_url"):
        missing_imgs += 1

    variants = d.get("variants", [])
    for v in variants:
        if isinstance(v, dict):
            if v.get("option_values"):
                for ov in v["option_values"]:
                    option_names[ov.get("option_name", "")] += 1

print("\n--- Product Types ---")
for k, v in types.most_common():
    print(f"  {k}: {v}")

print("\n--- Vendors ---")
for k, v in vendors.most_common():
    print(f"  {k}: {v}")

print("\n--- Availability ---")
for k, v in availability.most_common():
    print(f"  {k}: {v}")

print("\n--- Genders ---")
for k, v in genders.most_common():
    print(f"  {k}: {v}")

print("\n--- Option Names in Variants ---")
for k, v in option_names.most_common():
    print(f"  {k}: {v}")

print("\n--- Data Quality Checks ---")
print(f"  Files with \\ufffd replacement chars: {unicode_issues}")
print(f"  Products with missing images: {missing_imgs}")
print(f"  Products with zero/invalid price: {zero_prices}")
