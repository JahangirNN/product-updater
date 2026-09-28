import re
import httpx

client = httpx.Client(follow_redirects=True, timeout=15.0)

all_proposed = [
    # Women
    ("Women All Bags", "/collections/womens-handbags"),
    ("Women Coach", "/collections/womens-handbags?filter.p.vendor=COACH"),
    ("Women JW PEI", "/collections/jw-pei"),
    ("Women MK", "/collections/womens-handbags?filter.p.vendor=MICHAEL+Michael+Kors"),
    ("Women Shoulder Bags", "/collections/womens-handbags/shoulder-bags"),
    ("Women Crossbody", "/collections/womens-handbags?filter.p.tag=Crossbody+Bags"),
    ("Women Totes", "/collections/womens-handbags/totes"),
    ("Women Wallets", "/collections/wallets-accessories?filter.p.tag=Women"),

    # Men
    ("Men All Bags", "/collections/designer-bags?filter.p.tag=Men"),
    ("Men Coach", "/collections/designer-bags?filter.p.tag=Men&filter.p.vendor=COACH"),
    ("Men MK", "/collections/designer-bags?filter.p.tag=Men&filter.p.vendor=MICHAEL+Michael+Kors"),
    ("Men Briefcases & Satchels", "/collections/designer-bags?filter.p.tag=Men&filter.p.tag=Satchels"),
    ("Men Backpacks", "/collections/designer-bags?filter.p.tag=Men&filter.p.tag=Backpacks"),
    ("Men Messengers", "/collections/designer-bags?filter.p.tag=Men&filter.p.tag=Crossbody+%26+Messenger+Bags"),
    ("Men Wallets", "/collections/wallets-accessories?filter.p.tag=Men"),

    # Brands A-Z
    ("Brand Coach Bags", "/collections/designer-bags?filter.p.vendor=COACH"),
    ("Brand Coach Men", "/collections/designer-bags?filter.p.tag=Men&filter.p.vendor=COACH"),
    ("Brand JW PEI", "/collections/jw-pei"),
    ("Brand JW PEI Totes", "/collections/jw-pei/totes"),
    ("Brand MK All", "/collections/michael-kors"),
    ("Brand MK Watches", "/collections/michael-kors-watches"),
    ("Brand MK Sunglasses", "/collections/designer-eyewear?filter.p.vendor=Michael+Kors")
]

print("=" * 80)
print("AUDITING ALL NAVIGATION URLS ON LIVE STOREFRONT")
print("=" * 80)

results = []
for label, path in all_proposed:
    url = "https://therareavenue.com" + path
    try:
        r = client.get(url)
        status = r.status_code
        
        # Extract product URLs specifically from main collection grid
        # Avoid counting menu or drawer links by finding /products/ links
        product_links = list(set(re.findall(r'href="(/products/[a-z0-9\-]+)"', r.text)))
        prod_count = len(product_links)
        
        # Check if the page returned 200 and has valid structure
        is_200 = (status == 200)
        
        if is_200 and prod_count > 0:
            category = "LIVE_WITH_PRODUCTS"
            status_str = f"[{status}] ACTIVE ({prod_count} prods)"
        elif is_200 and prod_count == 0:
            category = "ROUTED_PENDING_PUBLICATION"
            status_str = f"[{status}] PENDING CHANNEL PUB (0 prods)"
        else:
            category = "BROKEN"
            status_str = f"[{status}] FAILED"

        print(f"{status_str:35} | {label:26} -> {path}")
        results.append((label, path, status, prod_count, category))
    except Exception as e:
        print(f"[ERR] FAILED                      | {label:26} -> {e}")
        results.append((label, path, 0, 0, "ERROR"))

print("=" * 80)
active = [r for r in results if r[4] == "LIVE_WITH_PRODUCTS"]
pending = [r for r in results if r[4] == "ROUTED_PENDING_PUBLICATION"]
broken = [r for r in results if r[4] in ("BROKEN", "ERROR")]

print(f"AUDIT SUMMARY:")
print(f"  Live active URLs with published products: {len(active)}/{len(all_proposed)}")
print(f"  Valid 200 URLs awaiting sales channel publication (Coach/MK): {len(pending)}/{len(all_proposed)}")
print(f"  Broken URLs (404/error): {len(broken)}/{len(all_proposed)}")
print("=" * 80)
