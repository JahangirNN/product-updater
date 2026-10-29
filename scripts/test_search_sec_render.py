import urllib.request
import re

url = 'https://therareavenue.com/search?q=Wallet+vendor:COACH+tag:Wallets&section_id=template--29325263995046__main'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

print("Length:", len(html))
print("Has product list:", 'product-list' in html)
cards = re.findall(r'data-vendor="([^"]+)"', html)
print(f"Cards count: {len(cards)}, vendors: {set(cards)}")
