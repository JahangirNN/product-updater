import urllib.request
import re

urls = [
    'https://therareavenue.com/collections/coach/men',
    'https://therareavenue.com/collections/coach/women',
    'https://therareavenue.com/collections/coach/shoes-footwear',
    'https://therareavenue.com/collections/coach/shoes-footwear+men',
    'https://therareavenue.com/collections/coach/men+shoes-footwear',
    'https://therareavenue.com/collections/men/coach',
    'https://therareavenue.com/collections/men/shoes-footwear',
    'https://therareavenue.com/collections/men/footwear',
    'https://therareavenue.com/collections/women/coach',
    'https://therareavenue.com/collections/women/shoes-footwear',
    'https://therareavenue.com/collections/michael-kors/men',
    'https://therareavenue.com/collections/michael-kors/shoes-footwear',
    'https://therareavenue.com/collections/michael-kors/men+shoes-footwear',
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
