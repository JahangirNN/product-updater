import json
import os

DB_DIR = "product-updater/storage/db/sephora/products"
BRANDS = [
    "Summer Fridays", "Gisou", "Haus Labs", "PATRICK TA", "Saie",
    "Tower 28 Beauty", "MERIT", "Westman Atelier", "Kosas", "rhode",
    "Glossier", "MAKEUP BY MARIO", "Hourglass", "REFY"
]

found = {}
for fn in os.listdir(DB_DIR):
    if not fn.endswith(".json"):
        continue
    fp = os.path.join(DB_DIR, fn)
    try:
        with open(fp, encoding="utf-8") as f:
            p = json.load(f)
            brand = p.get("brand") or p.get("vendor") or ""
            # match brand case-insensitively
            for b in BRANDS:
                if b.lower() == brand.lower() or b.lower() in brand.lower():
                    if b not in found:
                        found[b] = {
                            "id": p.get("id"),
                            "title": p.get("title"),
                            "brand": brand,
                            "variants_count": len(p.get("variants", [])),
                            "file": fn
                        }
    except Exception as e:
        pass

print(f"Found {len(found)}/{len(BRANDS)} brands:")
for b, info in found.items():
    print(f"- {b}: {info['title']} ({info['variants_count']} variants, file: {info['file']})")

missing = [b for b in BRANDS if b not in found]
if missing:
    print("Missing brands:", missing)
