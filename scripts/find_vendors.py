import urllib.request
import re

for term in ['Wallet', 'Bag', 'Watch']:
    url = f'https://therareavenue.com/search?q={term}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
    # Let's find vendors from product cards or json
    # In theme, how is vendor rendered in product-card?
    vendors = set(re.findall(r'class="product-card__vendor[^"]*">([^<]+)</div>', html))
    if not vendors:
        # Check title or links
        links = re.findall(r'/products/([^"?]+)', html)
        print(f"Term '{term}': {len(links)} products found")
    else:
        print(f"Term '{term}': vendors found = {vendors}")
