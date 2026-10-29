import httpx

client = httpx.Client(follow_redirects=True, timeout=15.0)

test_urls = [
    "/collections/womens-handbags?filter.p.vendor=COACH",
    "/collections/womens-handbags?filter.p.vendor=Michael+Kors",
    "/collections/womens-handbags?filter.p.vendor=MICHAEL+Michael+Kors",
    "/collections/womens-handbags?filter.p.vendor=JW+PEI",
    "/collections/womens-handbags/coach",
    "/collections/womens-handbags/COACH",
    "/collections/womens-handbags/michael-kors",
    "/collections/designer-bags?filter.p.vendor=COACH",
    "/collections/designer-bags?filter.p.vendor=MICHAEL+Michael+Kors",
    "/collections/designer-bags?filter.p.vendor=JW+PEI",
    "/collections/coach",
    "/collections/jw-pei",
    "/collections/michael-kors"
]

print("=== TESTING VENDOR FILTER URLS ===")
for u in test_urls:
    url = "https://therareavenue.com" + u
    r = client.get(url)
    has_card = 'class="product-card' in r.text
    empty = "0 products" in r.text
    print(f"[{r.status_code}] {'CARDS' if has_card else 'EMPTY'} | {u}")
