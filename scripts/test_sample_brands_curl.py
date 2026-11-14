import json
import time
from curl_cffi import requests
from parsel import Selector

with open("product-updater/storage/sephora_discovered_urls.json", "r", encoding="utf-8") as f:
    manifest = json.load(f)

products = manifest["products"]
# Pick 5 products from different brands
sample_prods = []
seen_brands = set()
for p in products:
    b = p["brand"]
    if b not in seen_brands:
        sample_prods.append(p)
        seen_brands.add(b)
    if len(sample_prods) >= 5:
        break

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

print(f"Testing 5 products across brands with curl_cffi:")
for idx, p in enumerate(sample_prods, 1):
    url = p["url"]
    t0 = time.perf_counter()
    r = requests.get(url, headers=headers, impersonate="chrome124", timeout=20)
    dur = time.perf_counter() - t0
    
    # Extract JSON
    sel = Selector(r.text)
    scripts = sel.css("script::text").getall()
    pdata = None
    for s in scripts:
        s_clean = s.strip()
        if s_clean.startswith('{"page":') and '"product":' in s_clean:
            try:
                data = json.loads(s_clean)
                pdata = data.get("page", {}).get("product")
                if pdata:
                    break
            except Exception:
                pass
                
    if pdata:
        title = pdata.get("productDetails", {}).get("displayName") or pdata.get("displayName")
        variants = pdata.get("regularChildSkus", [])
        v_count = len(variants) if variants else 1
        print(f"[{idx}/5] {p['brand']:<16} | Status {r.status_code} ({dur:.2f}s) | Title: {title[:30]} | Variants: {v_count}")
    else:
        print(f"[{idx}/5] {p['brand']:<16} | FAILED to extract JSON (Status {r.status_code}, len={len(r.text)})")
    time.sleep(0.5)
