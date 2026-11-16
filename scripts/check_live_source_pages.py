import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

# 1. JW PEI
url_jw = "https://www.jwpei.com/products/maelle-faux-ostrich-grain-dachshund-charm-double-handle-bag-brown.js"
url_jw_html = "https://www.jwpei.com/products/maelle-faux-ostrich-grain-dachshund-charm-double-handle-bag-brown"

print("--- Checking JW PEI ---")
try:
    # Shopify stores have .js or .json endpoints
    r = requests.get(url_jw, headers=headers, timeout=10)
    print("JW PEI .js status:", r.status_code)
    if r.status_code == 200:
        data = r.json()
        print("JW PEI title:", data.get("title"))
        print("JW PEI live images count:", len(data.get("images", [])))
        print("JW PEI sample image:", data.get("images", [])[:2])
    else:
        r2 = requests.get(url_jw_html, headers=headers, timeout=10)
        print("JW PEI HTML status:", r2.status_code)
except Exception as e:
    print("JW PEI error:", e)

# 2. Jomashop
print("\n--- Checking Jomashop ---")
url_joma = "https://www.jomashop.com/tissot-watch-t099-207-22-118-02.html"
try:
    r = requests.get(url_joma, headers=headers, timeout=10)
    print("Jomashop status:", r.status_code)
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, "html.parser")
        imgs = [img.get("src") for img in soup.find_all("img") if img.get("src")]
        print("Jomashop total imgs found:", len(imgs))
        prod_imgs = [i for i in imgs if "product" in i.lower() or "tissot" in i.lower()]
        print("Jomashop sample product imgs:", prod_imgs[:3])
except Exception as e:
    print("Jomashop error:", e)
