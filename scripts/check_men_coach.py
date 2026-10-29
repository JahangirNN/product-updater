import urllib.request
import re

url = 'https://therareavenue.com/collections/men?filter.p.vendor=COACH'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    html = resp.read().decode('utf-8')
    # Find all product cards with their title and vendor
    # In prestige, product cards have vendor and title
    vendors = re.findall(r'class="product-card__vendor"[^>]*>([^<]+)<', html)
    titles = re.findall(r'class="product-card__title"[^>]*>.*?<a[^>]*>([^<]+)</a>', html, re.DOTALL)
    if not titles:
        # Let's search for product-item
        matches = re.findall(r'href="(/products/[^"]+)".*?>([^<]+)</a>', html)
        print(f'Total matches: {len(matches)}')
        for m in matches[:15]:
            print(m)
    print('Vendors found:', set(vendors))
