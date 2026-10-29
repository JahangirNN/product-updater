import urllib.request
import re

urls = [
    'https://therareavenue.com/collections/coach?filter.p.tag=Footwear',
    'https://therareavenue.com/collections/coach?filter.p.tag=Footwear&filter.p.tag=Men',
    'https://therareavenue.com/collections/coach?filter.p.tag=Footwear&filter.v.tags=Men',
    'https://therareavenue.com/collections/men?filter.p.vendor=COACH&filter.p.tag=Footwear',
    'https://therareavenue.com/collections/women?filter.p.vendor=COACH&filter.p.tag=Footwear',
    'https://therareavenue.com/collections/coach?filter.p.tag=Footwear&filter.p.tag=Women'
]

req_headers = {'User-Agent': 'Mozilla/5.0'}

for u in urls:
    req = urllib.request.Request(u, headers=req_headers)
    try:
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode('utf-8')
            # Look for product titles in product card links or titles
            card_titles = re.findall(r'<span class="product-card__title">.*?<a[^>]*>([^<]+)</a>', html, re.DOTALL)
            if not card_titles:
                card_titles = re.findall(r'<a[^>]*class="[^"]*product-card__title[^"]*"[^>]*>([^<]+)</a>', html)
            if not card_titles:
                card_titles = re.findall(r'class="bold line-clamp">([^<]+)<', html)
            if not card_titles:
                card_titles = re.findall(r'product-card__title">([^<]+)<', html)
            print(f'URL: {u}')
            print(f'Found {len(card_titles)} products. Sample: {card_titles[:5]}')
            print('-' * 40)
    except Exception as e:
        print(f'URL: {u} -> Error: {e}')

