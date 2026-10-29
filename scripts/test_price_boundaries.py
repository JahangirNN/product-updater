import requests
import re

def test_filter(label, url):
    print("=" * 60)
    print(f"Testing {label}: {url}")
    resp = requests.get(url)
    matches = re.findall(r'(<product-card\b[^>]*>.*?)(?=<product-card|\Z)', resp.text, re.DOTALL)
    print(f"Total product cards: {len(matches)}")
    for i, m in enumerate(matches[:5]):
        h = re.search(r'handle="([^"]*)"', m)
        handle = h.group(1) if h else "Unknown"
        p = re.search(r'<price-list\b[^>]*>(.*?)</price-list>', m, re.DOTALL)
        p_text = re.sub(r'<[^>]+>', ' ', p.group(1)).strip() if p else "None"
        p_text = re.sub(r'\s+', ' ', p_text)
        print(f"  [{i+1}] {handle}: {p_text}")

test_filter("Only GTE >= 20000", "https://therareavenue.com/collections/womens-handbags?filter.p.vendor=JW+PEI&filter.v.price.gte=20000")
test_filter("Only LTE <= 10000", "https://therareavenue.com/collections/womens-handbags?filter.p.vendor=JW+PEI&filter.v.price.lte=10000")
test_filter("No Price Filter", "https://therareavenue.com/collections/womens-handbags?filter.p.vendor=JW+PEI")
