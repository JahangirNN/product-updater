import urllib.request
import re

url = 'https://therareavenue.com/search?q=Wallet'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

sec_matches = re.findall(r'id="(shopify-section-[^"]*main-search[^"]*)"', html)
print("Search section matches:", sec_matches)
if sec_matches:
    sec_id = sec_matches[0].replace('shopify-section-', '')
    print("Main search section id:", sec_id)
    
    # Test section rendering
    test_sec_url = f'https://therareavenue.com/search?q=Wallet+vendor:COACH&section_id={sec_id}'
    req2 = urllib.request.Request(test_sec_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req2) as resp2:
        sec_html = resp2.read().decode('utf-8', errors='ignore')
    print("Section HTML response length:", len(sec_html))
    print("Has product list:", 'product-list' in sec_html)
