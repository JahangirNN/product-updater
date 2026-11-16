import json
import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
}

with open("product-updater/storage/zero_image_audit_detail.json", "r", encoding="utf-8") as f:
    items = json.load(f)

sephora_items = [item for item in items if item.get("store") == "sephora"]
first = sephora_items[0]
print("First item title:", first["title"], flush=True)
print("File:", first["file"], flush=True)
with open(first["file"], "r", encoding="utf-8") as f:
    prod = json.load(f)
imgs = prod.get("images", [])
print(f"Total images in file: {len(imgs)}", flush=True)
if imgs:
    print(f"Img 0: {imgs[0]}", flush=True)
    try:
        r = requests.get(imgs[0], headers=headers, timeout=5)
        print(f"Status: {r.status_code}, Bytes: {len(r.content)}", flush=True)
    except Exception as e:
        print(f"Fetch error: {e}", flush=True)
