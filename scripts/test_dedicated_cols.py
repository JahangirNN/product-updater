import httpx
import re

client = httpx.Client(follow_redirects=True, timeout=15.0)

test_urls = [
    ("Coach Collection", "/collections/coach"),
    ("Michael Kors Collection", "/collections/michael-kors"),
    ("JW PEI Collection", "/collections/jw-pei"),
    ("Men's Bags Collection", "/collections/mens-bags"),
    ("Women's Handbags", "/collections/womens-handbags"),
    ("Crossbody Bags Collection", "/collections/crossbody-bags"),
    ("Totes Collection", "/collections/totes"),
    ("Wallets Accessories", "/collections/wallets-accessories")
]

for label, path in test_urls:
    url = f"https://therareavenue.com{path}"
    r = client.get(url)
    product_links = list(set(re.findall(r'href="(/products/[^"?#]+)"', r.text)))
    empty_notice = "0 products" in r.text or "no products" in r.text.lower()
    print(f"[{r.status_code}] {label:26} ({path}) -> {len(product_links)} products found")
    if product_links:
        print("   Sample:", product_links[0])
