import urllib.request
import re
from collections import Counter

for test_url in [
    'https://therareavenue.com/search?q=Wallet+vendor:COACH',
    'https://therareavenue.com/search?q=vendor:COACH',
    'https://therareavenue.com/search?q=Wallet+COACH',
    'https://therareavenue.com/search?q=Wallet+tag:COACH',
    'https://therareavenue.com/search?q=Wallet&q=COACH',
]:
    req = urllib.request.Request(test_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
    vendors = re.findall(r'data-vendor="([^"]+)"', html)
    print(f"URL: {test_url}")
    print(f"  Total cards: {len(vendors)}, Vendors: {Counter(vendors)}")
