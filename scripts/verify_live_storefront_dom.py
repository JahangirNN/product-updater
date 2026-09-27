import urllib.request
import re

url = "https://therareavenue.com"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req) as resp:
    html = resp.read().decode("utf-8")

checks = [
    "/collections/womens-handbags",
    "/collections/designer-bags/men",
    "/collections/designer-bags/coach",
    "/collections/wallets-accessories",
    "Shop All Luxury Bags",
    "Shop All Men's Bags"
]

print("LIVE STOREFRONT DOM VERIFICATION:")
for c in checks:
    present = c in html
    print(f"  [{'FOUND' if present else 'MISSING'}] {c}")
