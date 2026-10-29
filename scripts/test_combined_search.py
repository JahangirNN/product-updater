import urllib.request
import re
from collections import Counter

test_url = 'https://therareavenue.com/search?q=Wallet+vendor:COACH&filter.v.availability=1&filter.v.price.gte=5000&filter.v.price.lte=20000'
req = urllib.request.Request(test_url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

m = re.search(r'([0-9]+)\s+results\s+for', html)
count = m.group(1) if m else 'N/A'
vendors = re.findall(r'data-vendor="([^"]+)"', html)
print(f"URL: {test_url}")
print(f"  Count: {count}, rendered cards: {len(vendors)}")
print(f"  Vendors: {Counter(vendors)}")
