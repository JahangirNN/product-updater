import os
import sys
import glob
import json
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

def check_url(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}, method='HEAD')
        with urllib.request.urlopen(req, timeout=5) as resp:
            return url, True
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):
            return url, False
        return url, True
    except Exception:
        return url, True

urls_map = {} # url -> list of (store, handle, variant_title, sku)

for store in ["jwpei", "coach", "michaelkors"]:
    pattern = os.path.join(PROJECT_ROOT, "storage", "db", store, "products", "*.json")
    for f in glob.glob(pattern):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                d = json.load(fp)
        except Exception:
            continue
        h = d.get("handle")
        for v in d.get("variants") or []:
            if isinstance(v, dict):
                img = v.get("image_url") or v.get("image") or (v.get("images") or [None])[0]
                if img and isinstance(img, str) and img.startswith("http"):
                    if img not in urls_map:
                        urls_map[img] = []
                    urls_map[img].append((store, h, v.get("title"), v.get("sku")))

all_urls = list(urls_map.keys())
print(f"Total unique variant image URLs across JW PEI, Coach, MK: {len(all_urls)}")

broken_urls = {}
with ThreadPoolExecutor(max_workers=30) as executor:
    futures = {executor.submit(check_url, u): u for u in all_urls}
    for fut in as_completed(futures):
        u = futures[fut]
        try:
            url, ok = fut.result()
            if not ok:
                broken_urls[url] = urls_map[url]
                print(f"BROKEN 404: {url} -> {urls_map[url][0]}")
        except Exception:
            pass

print(f"\nTotal broken 404 variant image URLs found: {len(broken_urls)}")
out_file = os.path.join(PROJECT_ROOT, "storage", "broken_variant_image_urls.json")
with open(out_file, "w", encoding="utf-8") as fp:
    json.dump(broken_urls, fp, indent=2)
print(f"Saved broken URLs to: {out_file}")
