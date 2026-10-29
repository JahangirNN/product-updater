import urllib.request
import re

url = 'https://therareavenue.com/search?q=Watch'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

vendors = re.findall(r'data-vendor="([^"]+)"', html)
from collections import Counter
counts = Counter(vendors)
print(f"Total cards with data-vendor: {len(vendors)}")
print("Vendor counts in Wallet search results:")
for v, c in counts.most_common():
    print(f"  {v}: {c}")
