import httpx

client = httpx.Client(follow_redirects=True, timeout=15.0)

test_links = [
    # Women
    ("Women Handbags", "/collections/womens-handbags"),
    ("Women Shoulder Bags", "/collections/womens-handbags/shoulder-bags"),
    ("Women Crossbody", "/collections/womens-handbags/crossbody-bags"),
    ("Women Totes", "/collections/womens-handbags/totes"),
    ("Women Wallets", "/collections/womens-handbags/wallets"),
    ("Women Wallets 2", "/collections/wallets-accessories/women"),
    ("Women Coach", "/collections/womens-handbags/coach"),
    ("Women JW PEI", "/collections/jw-pei"),
    ("Women MK", "/collections/womens-handbags/michael-kors"),

    # Men
    ("Men Bags All", "/collections/mens-bags"),
    ("Men Briefcases", "/collections/mens-bags/briefcase"),
    ("Men Briefcases Satchels", "/collections/mens-bags/satchels"),
    ("Men Backpacks", "/collections/mens-bags/backpacks"),
    ("Men Messengers", "/collections/mens-bags/messenger-bags"),
    ("Men Messengers 2", "/collections/mens-bags/crossbody-bags"),
    ("Men Wallets", "/collections/mens-bags/wallets"),
    ("Men Wallets 2", "/collections/wallets-accessories/men"),
    ("Men Coach", "/collections/mens-bags/coach"),
    ("Men MK", "/collections/mens-bags/michael-kors")
]

print("=" * 80)
print("TESTING WOMEN & MEN BAG NAVIGATION LINKS")
print("=" * 80)

for label, path in test_links:
    url = "https://therareavenue.com" + path
    try:
        r = client.get(url)
        empty = "no products" in r.text.lower() or "there are no products" in r.text.lower()
        print(f"[{r.status_code}] {'EMPTY ' if empty else 'OK    '} {label:24} -> {path}")
    except Exception as e:
        print(f"[ERR]       {label:24} -> {path} ({e})")
