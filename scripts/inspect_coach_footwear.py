import urllib.request
import re

urls = [
    'https://therareavenue.com/collections/coach?filter.p.tag=Footwear',
    'https://therareavenue.com/collections/coach?filter.p.tag=Footwear&filter.p.tag=Men',
    'https://therareavenue.com/collections/men?filter.p.vendor=COACH&filter.p.tag=Footwear',
    'https://therareavenue.com/collections/men?filter.p.vendor=COACH',
    'https://therareavenue.com/collections/coach?filter.p.tag=Men',
    'https://therareavenue.com/collections/mens-shoes',
    'https://therareavenue.com/collections/mens-shoes?filter.p.vendor=COACH'
]

req_headers = {'User-Agent': 'Mozilla/5.0'}

for u in urls:
    req = urllib.request.Request(u, headers=req_headers)
    try:
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode('utf-8')
            links = sorted(list(set(re.findall(r'href=["\'](/products/[^"\']+)["\']', html))))
            print(f'URL: {u}')
            print(f'Total product links: {len(links)}')
            for l in links[:5]:
                print(' ', l)
            print('-' * 50)
    except Exception as e:
        print(f'URL: {u} -> Error: {e}')
