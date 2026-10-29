import requests
import re

url = "https://therareavenue.com/search?q=JW+PEI&filter.v.price.gte=15000&filter.v.price.lte=31560"
resp = requests.get(url)

cards = re.findall(r'<product-card\b[^>]*>', resp.text)
print(f"Total product cards on search page: {len(cards)}")

matches = re.findall(r'(<product-card\b[^>]*>.*?)(?=<product-card|\Z)', resp.text, re.DOTALL)
for i, m in enumerate(matches[:5]):
    h = re.search(r'handle="([^"]*)"', m)
    handle = h.group(1) if h else "Unknown"
    p = re.search(r'<price-list\b[^>]*>(.*?)</price-list>', m, re.DOTALL)
    p_text = re.sub(r'<[^>]+>', ' ', p.group(1)).strip() if p else "None"
    p_text = re.sub(r'\s+', ' ', p_text)
    print(f"  [{i+1}] {handle}: {p_text}")
