import os
import json

db_dir = "product-updater/storage/db/sephora/products"
if not os.path.exists(db_dir):
    print("Directory does not exist:", db_dir)
    exit(0)

files = os.listdir(db_dir)
print(f"Total files in {db_dir}: {len(files)}")
for f in files[:5]:
    with open(os.path.join(db_dir, f), "r", encoding="utf-8") as fp:
        p = json.load(fp)
    print(f"ID: {p['id']} | Brand: {p['brand']} | Title: {p['title'][:30]} | Price: Rs.{p['current_price']} | Avail: {p['availability']} | Variants: {len(p['variants'])}")
