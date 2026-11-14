import sys
import json
import re
from curl_cffi import requests
from parsel import Selector

url = "https://www.sephora.com/product/pocket-blush-P517483?skuId=2998102"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

print(f"Fetching PDP via curl_cffi: {url}")
r = requests.get(url, headers=headers, impersonate="chrome124", timeout=20)
print(f"Status: {r.status_code}, Length: {len(r.text)}")

sel = Selector(r.text)
scripts = sel.css("script::text").getall()
product_data = None

for s in scripts:
    s_clean = s.strip()
    if s_clean.startswith('{"page":') and '"product":' in s_clean:
        try:
            data = json.loads(s_clean)
            product_data = data.get("page", {}).get("product")
            if product_data:
                break
        except Exception as e:
            print("JSON parse error:", e)

if product_data:
    print("SUCCESS! Product Name:", product_data.get("displayName"))
    print("Product ID:", product_data.get("productId"))
    print("Brand:", product_data.get("brand", {}).get("displayName"))
    child_skus = product_data.get("regularChildSkus", [])
    print(f"Total Child SKUs (Variants): {len(child_skus)}")
    print("Top-level keys in product:", sorted(list(product_data.keys())))
    
    with open("product-updater/storage/sample_sephora_pdp.json", "w", encoding="utf-8") as f:
        json.dump(product_data, f, indent=2)
    print("Saved product-updater/storage/sample_sephora_pdp.json")
else:
    print("Could not find product JSON script block.")
