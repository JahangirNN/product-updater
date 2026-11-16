import os
import json
import requests

PROJECT_ROOT = "product-updater"
detail_path = os.path.join(PROJECT_ROOT, "storage", "zero_image_audit_detail.json")

with open(detail_path, "r", encoding="utf-8") as f:
    items = json.load(f)

sephora_items = [item for item in items if item.get("store") == "sephora"]
print(f"Testing {len(sephora_items)} Sephora products...")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
}

valid_count = 0
invalid_count = 0

for idx, item in enumerate(sephora_items, 1):
    fp = item.get("file")
    with open(fp, "r", encoding="utf-8") as f:
        prod = json.load(f)
    images = prod.get("images", [])
    if not images:
        print(f"[{idx}/{len(sephora_items)}] NO IMAGES IN DB: {item['title'][:40]}")
        invalid_count += 1
        continue
    
    test_img = images[0]
    try:
        r = requests.get(test_img, headers=headers, timeout=10)
        if r.status_code == 200 and len(r.content) > 1000:
            valid_count += 1
            print(f"[{idx}/{len(sephora_items)}] ✅ 200 OK ({len(r.content)} bytes, {len(images)} total): {item['vendor']} - {item['title'][:35]}")
        else:
            invalid_count += 1
            print(f"[{idx}/{len(sephora_items)}] ❌ HTTP {r.status_code}: {item['vendor']} - {item['title'][:35]}")
    except Exception as e:
        invalid_count += 1
        print(f"[{idx}/{len(sephora_items)}] ❌ Error {e}: {item['vendor']} - {item['title'][:35]}")

print("\n" + "=" * 50)
print(f"Sephora Image Test: {valid_count} Valid, {invalid_count} Invalid out of {len(sephora_items)}")
print("=" * 50)
