import urllib.request
import re
from collections import Counter

urls = [
    'https://therareavenue.com/search?q=Wallet+(vendor:COACH+OR+vendor:"Michael+Kors")',
    'https://therareavenue.com/search?q=Wallet+vendor:COACH+OR+vendor:"Michael+Kors"',
    'https://therareavenue.com/search?q=Wallet+(vendor:COACH+OR+vendor:"MICHAEL+Michael+Kors")',
    'https://therareavenue.com/search?q=Wallet+vendor:COACH',
    'https://therareavenue.com/search?q=Wallet+vendor:"MICHAEL+Michael+Kors"',
]

for url in urls:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            m = re.search(r'([0-9]+)\s+results\s+for', html)
            count = m.group(1) if m else 'N/A'
            vendors = re.findall(r'data-vendor="([^"]+)"', html)
            print(f"URL: {url}")
            print(f"  Count: {count}, cards: {len(vendors)}, Vendors: {Counter(vendors)}")
    except Exception as e:
        print(f"Error {url}: {e}")
