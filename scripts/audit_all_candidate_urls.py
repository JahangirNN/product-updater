import urllib.request
import re
from typing import Dict, List, Tuple

test_urls = [
    # Men's Footwear
    ("Men's Footwear Root", "https://therareavenue.com/collections/men/footwear"),
    ("Men's Coach Footwear", "https://therareavenue.com/collections/coach/men+footwear"),
    ("Men's MK Footwear", "https://therareavenue.com/collections/michael-kors/men+footwear"),
    ("Men's Salomon", "https://therareavenue.com/collections/men/salomon"),
    ("Men's On Running", "https://therareavenue.com/collections/men/on"),
    ("Men's HOKA", "https://therareavenue.com/collections/men/hoka"),

    # Women's Footwear
    ("Women's Footwear Root", "https://therareavenue.com/collections/women/footwear"),
    ("Women's Coach Footwear", "https://therareavenue.com/collections/coach/women+footwear"),
    ("Women's MK Footwear", "https://therareavenue.com/collections/michael-kors/women+footwear"),
    ("Women's On Running", "https://therareavenue.com/collections/women/on"),
    ("Women's Salomon", "https://therareavenue.com/collections/women/salomon"),
    ("Women's HOKA", "https://therareavenue.com/collections/women/hoka"),

    # Footwear General (in Brands)
    ("Brand Coach Footwear", "https://therareavenue.com/collections/coach/footwear"),
    ("Brand MK Footwear", "https://therareavenue.com/collections/michael-kors/footwear"),
    ("All Salomon", "https://therareavenue.com/collections/all/salomon"),
    ("All On Running", "https://therareavenue.com/collections/all/on"),
    ("All HOKA", "https://therareavenue.com/collections/all/hoka"),

    # Men's Wallets
    ("Men's Wallets Root", "https://therareavenue.com/collections/wallets-leather-goods/men"),
    ("Men's Billfolds", "https://therareavenue.com/collections/wallets-leather-goods/men+billfolds"),
    ("Men's Card Cases", "https://therareavenue.com/collections/wallets-leather-goods/men+card-cases"),
    ("Men's Tech Wallets", "https://therareavenue.com/collections/wallets-leather-goods/men+tech-accessories"),
    ("Men's MK Wallets", "https://therareavenue.com/collections/wallets-leather-goods/men+michael-kors"),
    ("Men's Coach Wallets", "https://therareavenue.com/collections/wallets-leather-goods/men+coach"),

    # Women's Wallets
    ("Women's Wallets Root", "https://therareavenue.com/collections/wallets-leather-goods/women"),
    ("Women's Wristlets", "https://therareavenue.com/collections/wallets-leather-goods/women+wristlets"),
    ("Women's Card Cases", "https://therareavenue.com/collections/wallets-leather-goods/women+card-cases"),
    ("Women's Wallets Zip", "https://therareavenue.com/collections/wallets-leather-goods/women+wallets"),
    ("Women's MK Wallets", "https://therareavenue.com/collections/wallets-leather-goods/women+michael-kors"),
    ("Women's Coach Wallets", "https://therareavenue.com/collections/wallets-leather-goods/women+coach"),

    # Eyewear
    ("Women's Eyewear MK", "https://therareavenue.com/collections/womens-sunglasses/michael-kors"),
    ("Women's Cat-Eye", "https://therareavenue.com/collections/womens-sunglasses/cat-eye"),
    ("Women's Aviator", "https://therareavenue.com/collections/womens-sunglasses/aviator"),
    ("Women's Oversized", "https://therareavenue.com/collections/womens-sunglasses/oversized"),
    ("Men's Eyewear MK", "https://therareavenue.com/collections/mens-sunglasses/michael-kors"),
    ("Men's Aviator", "https://therareavenue.com/collections/mens-sunglasses/aviator"),
    ("Men's Navigator", "https://therareavenue.com/collections/mens-sunglasses/navigator"),
    ("Men's Wireframe", "https://therareavenue.com/collections/mens-sunglasses/wireframe"),

    # Men's Bags
    ("Men's Bags Root", "https://therareavenue.com/collections/mens-bags"),
    ("Men's Bags Coach", "https://therareavenue.com/collections/mens-bags/coach"),
    ("Men's Bags MK", "https://therareavenue.com/collections/mens-bags/michael-kors"),
    ("Men's Crossbody", "https://therareavenue.com/collections/mens-bags/crossbody-bags"),
    ("Men's Backpacks", "https://therareavenue.com/collections/mens-bags/backpacks"),
    ("Men's Satchels", "https://therareavenue.com/collections/mens-bags/satchels"),

    # Watches
    ("Men's Watches Root", "https://therareavenue.com/collections/mens-watches"),
    ("Men's Tissot", "https://therareavenue.com/collections/mens-watches/tissot"),
    ("Men's Citizen", "https://therareavenue.com/collections/mens-watches/citizen"),
    ("Men's Movado", "https://therareavenue.com/collections/mens-watches/movado"),
    ("Men's Seiko", "https://therareavenue.com/collections/mens-watches/seiko"),
    ("Men's Versace", "https://therareavenue.com/collections/mens-watches/versace"),
    ("Men's Ferragamo", "https://therareavenue.com/collections/mens-watches/ferragamo"),
]

req_headers = {'User-Agent': 'Mozilla/5.0'}

results = []
for label, u in test_urls:
    req = urllib.request.Request(u, headers=req_headers)
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            html = resp.read().decode('utf-8')
            links = re.findall(r'href=["\'](/products/[^"\']+)["\']', html)
            unique_links = []
            for l in links:
                clean_l = l.split('?')[0]
                if clean_l not in unique_links:
                    unique_links.append(clean_l)
            count = len(unique_links)
            sample = unique_links[:2]
            results.append((label, u, status, count, sample, None))
            print(f"[{status}] {label:24} -> {count} products | {u}")
    except Exception as e:
        results.append((label, u, 0, 0, [], str(e)))
        print(f"[ERR] {label:24} -> {e} | {u}")

print("\n--- SUMMARY OF EMPTY OR FAILED URLS ---")
for label, u, status, count, sample, err in results:
    if err or count == 0:
        print(f"FAIL: {label:24} status={status} count={count} err={err} url={u}")
