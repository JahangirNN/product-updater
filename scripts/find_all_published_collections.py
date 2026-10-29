import urllib.request
import time

all_handles = [
    'frontpage', 'men', 'women', 'instant-ship', 'shoes', 'wallet', 'belt', 'perfume-set',
    'backpack', 'footwear', 'handbags', 'bracelet', 'earrings', 'gift-section',
    'luxury-watches', 'versace', 'tissot', 'seiko', 'citizen', 'movado', 'mens-watches',
    'womens-watches', 'ferragamo', 'michael-kors-watches', 'designer-bags', 'premium-footwear',
    'wallets-accessories', 'womens-handbags', 'mens-bags', 'mens-shoes', 'womens-shoes',
    'jw-pei', 'coach', 'michael-kors', 'salomon', 'on-running', 'hoka', 'nike', 'jordan',
    'adidas', 'asics', 'designer-eyewear', 'womens-sunglasses', 'mens-sunglasses',
    'luxury-bags', 'womens-bags', 'crossbody-bags', 'totes', 'wallets-leather-goods',
    'womens-wallets', 'mens-wallets', 'ready-to-ship'
]

published = []
not_published = []

for h in all_handles:
    url = f"https://therareavenue.com/collections/{h}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            if r.status == 200:
                published.append(h)
    except Exception as e:
        not_published.append(h)

print(f"PUBLISHED ({len(published)}):", published)
print(f"NOT PUBLISHED ({len(not_published)}):", not_published)
