import httpx

client = httpx.Client(follow_redirects=True, timeout=15.0)

men_urls = [
    # Men's Bags All
    "/collections/designer-bags?filter.p.tag=Men",
    "/collections/designer-bags/men",
    
    # Coach Men
    "/collections/designer-bags?filter.p.tag=Men&filter.p.vendor=COACH",
    "/collections/designer-bags/coach+men",
    
    # MK Men
    "/collections/designer-bags?filter.p.tag=Men&filter.p.vendor=MICHAEL+Michael+Kors",
    "/collections/designer-bags/michael-kors+men",
    
    # Briefcases & Satchels
    "/collections/designer-bags?filter.p.tag=Men&filter.p.tag=Satchels",
    "/collections/designer-bags?filter.p.tag=Men&filter.p.tag=Satchels+%26+Top+Handles",
    
    # Backpacks
    "/collections/designer-bags?filter.p.tag=Men&filter.p.tag=Backpacks",
    
    # Messengers & Crossbody
    "/collections/designer-bags?filter.p.tag=Men&filter.p.tag=Crossbody+%26+Messenger+Bags",
    "/collections/designer-bags?filter.p.tag=Men&filter.p.tag=Crossbody+Bags",
    
    # Wallets
    "/collections/wallets-accessories?filter.p.tag=Men",
    "/collections/wallets-accessories/men",
    "/collections/designer-bags?filter.p.tag=Men&filter.p.tag=Wallets"
]

print("=== TESTING MEN'S NAVIGATION URLS ===")
for u in men_urls:
    url = "https://therareavenue.com" + u
    r = client.get(url)
    has_card = 'class="product-card' in r.text
    empty = "0 products" in r.text
    print(f"[{r.status_code}] {'CARDS' if has_card else 'EMPTY'} | {u}")
