import urllib.request
import re
from collections import Counter

urls = [
    'https://therareavenue.com/search?q=Wallet+tag:Wallets',
    'https://therareavenue.com/search?q=Wallet+product_type:Wallets',
    'https://therareavenue.com/search?q=Wallet+tag:"Satchels & Top Handles"',
    'https://therareavenue.com/search?q=Bag+tag:"Satchels & Top Handles"',
    'https://therareavenue.com/search?q=Bag+tag:satchels',
    'https://therareavenue.com/search?q=Bag+product_type:"Satchels & Top Handles"',
]

for url in urls:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            m = re.search(r'([0-9]+)\s+results\s+for', html)
            count = m.group(1) if m else 'N/A'
            prods = re.findall(r'<product-card[\s\S]*?</product-card>', html)
            print(f"URL: {url}")
            print(f"  Count: {count}, cards: {len(prods)}")
    except Exception as e:
        print(f"Error {url}: {e}")
