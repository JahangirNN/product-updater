import json
from curl_cffi import requests
from parsel import Selector

url = "https://www.sephora.com/product/hol26-holiday-trio-marshmallow-mini-P526100"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

session = requests.Session(impersonate="chrome124")
r = session.get(url, headers=headers, timeout=20)
print(f"Status: {r.status_code}, Length: {len(r.text)}")

sel = Selector(r.text)
scripts = sel.css("script::text").getall()
pdata = None
for s in scripts:
    s_clean = s.strip()
    if s_clean.startswith('{"page":') and '"product":' in s_clean:
        try:
            parsed = json.loads(s_clean)
            pdata = parsed.get("page", {}).get("product")
            if pdata:
                print("Found page.product in script!")
                break
        except Exception as e:
            print("JSON parse err:", e)

if pdata:
    print("Product ID:", pdata.get("productId"))
    print("Display Name:", pdata.get("displayName") or pdata.get("productDetails", {}).get("displayName"))
    print("currentSku:", pdata.get("currentSku", {}).get("skuId"), pdata.get("currentSku", {}).get("listPrice"))
    print("regularChildSkus:", pdata.get("regularChildSkus"))
else:
    print("NO page.product script! Checking other scripts...")
    for idx, s in enumerate(scripts):
        if "productId" in s or "P526100" in s:
            print(f"Script [{idx}] len {len(s)}: {s[:150]}...")
