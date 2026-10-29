import urllib.request
import re

urls = [
    'https://therareavenue.com/collections/all?filter.p.vendor=Salomon',
    'https://therareavenue.com/collections/all?filter.p.vendor=On',
    'https://therareavenue.com/collections/all?filter.p.vendor=HOKA',
    'https://therareavenue.com/collections/all?filter.p.vendor=COACH',
]


req_headers = {'User-Agent': 'Mozilla/5.0'}

for u in urls:
    req = urllib.request.Request(u, headers=req_headers)
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8')
        links = re.findall(r'href=["\'](/products/[^"\']+)["\']', html)
        # Deduplicate preserving order
        unique_links = []
        for l in links:
            clean_l = l.split('?')[0]
            if clean_l not in unique_links:
                unique_links.append(clean_l)
        print(f"URL: {u}")
        print(f"Total unique products on page 1: {len(unique_links)}")
        print("First 5 products:")
        for p in unique_links[:5]:
            print(f"  {p}")
        print("-" * 50)
