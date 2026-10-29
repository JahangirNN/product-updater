import requests
import re

html = requests.get('https://therareavenue.com/collections/womens-handbags?filter.p.vendor=JW+PEI&filter.v.price.gte=15000&filter.v.price.lte=31560').text

print("Active facets pills:")
for m in re.finditer(r'<facet-link[^>]*>(.*?)</facet-link>', html, re.DOTALL):
    print(" ", re.sub(r'\s+', ' ', m.group(0))[:120])

print("\nPrice-range inputs:")
for m in re.finditer(r'<input[^>]*name="filter\.v\.price\.[^>]*>', html):
    print(" ", m.group(0))

print("\nSample price-list elements:")
for m in re.finditer(r'<price-list[^>]*>(.*?)</price-list>', html, re.DOTALL):
    print(" ", re.sub(r'\s+', ' ', m.group(0))[:150])
    break
