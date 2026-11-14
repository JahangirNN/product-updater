import json

with open("product-updater/storage/db/sephora/products/08702e1da9320ab5.json", encoding="utf-8") as f:
    p = json.load(f)

for v in p.get("variants", []):
    if "3026283" in str(v):
        print(json.dumps(v, indent=2))
