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
        with urllib.request.urlopen(req, timeout=4) as resp:
            return url, resp.status == 200
    except urllib.error.HTTPError as e:
        if e.code in (404, 410, 403):
            return url, False
        return url, True # assume true on server error / rate limit
    except Exception:
        return url, True

# Collect unique variant image URLs across active stores
urls = set()
url_to_var = {}

stores = ["jwpei", "coach", "michaelkors"]
for s in stores:
    for f in glob.glob(os.path.join(PROJECT_ROOT, "storage", "db", s, "products", "*.json")):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                d = json.load(fp)
        except Exception:
            continue
        for v in d.get("variants") or []:
            if isinstance(v, dict):
                img = v.get("image_url") or v.get("image") or (v.get("images") or [None])[0]
                if img and isinstance(img, str) and img.startswith("http"):
                    urls.add(img)
                    if img not in url_to_var:
                        url_to_var[img] = (s, d.get("handle"), v.get("title"))

print(f"Total unique variant image URLs in JW PEI, Coach, MK: {len(urls)}")

# Sample check 500 URLs to see error rate
sample_urls = list(urls)[:500]
print(f"Testing sample of {len(sample_urls)} URLs...")
broken = []
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = [executor.submit(check_url, u) for u in sample_urls]
    for fut in as_completed(futures):
        u, ok = fut.result()
        if not ok:
            broken.append(u)
            print(f"BROKEN: {u} -> {url_to_var[u]}")

print(f"\nBroken URLs in sample: {len(broken)} / {len(sample_urls)}")
