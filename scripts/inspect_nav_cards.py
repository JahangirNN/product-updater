import httpx
import re

client = httpx.Client(follow_redirects=True, timeout=15.0)

for url_label, path in [
    ("Women Coach", "/collections/womens-handbags?filter.p.vendor=COACH"),
    ("Women MK", "/collections/womens-handbags?filter.p.vendor=MICHAEL+Michael+Kors"),
    ("Men Coach", "/collections/designer-bags?filter.p.tag=Men&filter.p.vendor=COACH"),
    ("Men MK", "/collections/designer-bags?filter.p.tag=Men&filter.p.vendor=MICHAEL+Michael+Kors"),
    ("Women JW PEI", "/collections/jw-pei")
]:
    url = f"https://therareavenue.com{path}"
    r = client.get(url)
    product_links = list(set(re.findall(r'href="(/products/[^"?#]+)"', r.text)))
    empty_notice = "0 products" in r.text or "no products" in r.text.lower()
    print(f"=== {url_label} ({path}) ===")
    print(f"Status: {r.status_code}, Found product links: {len(product_links)}, empty_notice: {empty_notice}")
    for pl in product_links[:3]:
        print(f"  Link: {pl}")

