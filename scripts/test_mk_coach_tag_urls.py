import urllib.request
import re

urls = [
    'https://therareavenue.com/collections/michael-kors/women+footwear',
    'https://therareavenue.com/collections/michael-kors/women+shoes',
]


req_headers = {'User-Agent': 'Mozilla/5.0'}

for u in urls:
    req = urllib.request.Request(u, headers=req_headers)
    try:
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode('utf-8')
            links = re.findall(r'href=["\'](/products/[^"\']+)["\']', html)
            unique_links = []
            for l in links:
                clean_l = l.split('?')[0]
                if clean_l not in unique_links:
                    unique_links.append(clean_l)
            print(f"URL: {u} -> Status: {resp.status}, Products: {len(unique_links)}")
            if unique_links:
                for p in unique_links[:4]:
                    print(f"   {p}")
    except Exception as e:
        print(f"URL: {u} -> Error: {e}")
    print("-" * 50)
