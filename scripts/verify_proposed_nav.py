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

print("=== VERIFYING ALL PROPOSED URLS ===")
failed = []
for label, path in all_proposed:
    url = "https://therareavenue.com" + path
    r = client.get(url)
    has_card = 'class="product-card' in r.text
    empty = "0 products" in r.text
    status = r.status_code
    is_ok = (status == 200 and has_card and not empty)
    if is_ok:
        print(f"[{status}] OK     | {label:26} -> {path}")
    else:
        print(f"[{status}] FAILED | {label:26} -> {path} (has_card={has_card}, empty={empty})")
        failed.append((label, path, status, has_card, empty))

print("=" * 80)
if failed:
    print(f"FAILED ({len(failed)}):", failed)
else:
    print(f"ALL {len(all_proposed)} PROPOSED URLS PASSED WITH 200 OK AND PRODUCT CARDS!")
