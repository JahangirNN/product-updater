import httpx

client = httpx.Client(follow_redirects=True, timeout=15.0)

for url_path in [
    "/collections/womens-handbags/coach",
    "/collections/womens-handbags/COACH",
    "/collections/womens-handbags/crossbody-bags",
    "/collections/womens-handbags/michael-kors",
    "/collections/womens-handbags/shoulder-bags",
    "/collections/womens-handbags/totes",
    "/collections/designer-bags/coach+men",
    "/collections/designer-bags/michael-kors+men",
    "/collections/designer-bags/men"
]:
    url = "https://therareavenue.com" + url_path
    r = client.get(url)
    text = r.text
    # Count product titles or card instances in the HTML
    has_card = 'class="product-card' in text or 'class="product-item' in text or 'product-card' in text
    empty_notice = "no products found" in text.lower() or "there are no products" in text.lower()
    print(f"Path: {url_path:45} | Status: {r.status_code} | EmptyNotice: {empty_notice} | HasCard: {has_card}")
