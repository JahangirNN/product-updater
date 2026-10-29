import urllib.request
import re

url = 'https://therareavenue.com/search?q=Wallet'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

secs = re.findall(r'id="(shopify-section-[^"]+)"', html)
for s in secs:
    print("Section:", s)
