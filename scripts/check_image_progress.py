import os
import json

p_dir = "product-updater/storage/db/sephora/products"
files = [fn for fn in os.listdir(p_dir) if fn.endswith(".json")]
img_synced = sum(1 for fn in files if json.load(open(os.path.join(p_dir, fn), encoding="utf-8")).get("shopify_image_synced"))
print(f"Image Upload Progress: {img_synced} / {len(files)} ({(img_synced/len(files))*100:.1f}%)")
