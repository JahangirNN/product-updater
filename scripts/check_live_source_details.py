import requests
from bs4 import BeautifulSoup
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
}

# 1. Test new JW PEI image
jw_img = "https://cdn.shopify.com/s/files/1/0150/6292/5412/files/1790242346455-h5g04eada1f.jpg?v=1790243815"
r = requests.get(jw_img, headers=headers, timeout=10)
print(f"JW PEI new image status={r.status_code}, length={len(r.content)}")

# 2. Check Jomashop Next Data
url_joma = "https://www.jomashop.com/tissot-watch-t099-207-22-118-02.html"
r_joma = requests.get(url_joma, headers=headers, timeout=10)
soup = BeautifulSoup(r_joma.text, "html.parser")
next_data = soup.find("script", id="__NEXT_DATA__")
if next_data:
    try:
        j = json.loads(next_data.string)
        props = j.get("props", {}).get("pageProps", {})
        prod = props.get("product") or props.get("initialState", {}).get("product", {})
        print("Jomashop product keys:", list(prod.keys()) if isinstance(prod, dict) else type(prod))
        if isinstance(prod, dict):
            print("Jomashop product images:", prod.get("images") or prod.get("mediaGallery") or prod.get("image"))
    except Exception as e:
        print("Jomashop next data parse error:", e)
else:
    print("Jomashop __NEXT_DATA__ not found. Checking script tags...")
    for s in soup.find_all("script"):
        if s.string and "product" in s.string.lower() and "cdn2.jomashop.com" in s.string:
            print("Found script with cdn2.jomashop.com:", s.string[:200])
            break
