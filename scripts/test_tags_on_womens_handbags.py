import httpx

client = httpx.Client(follow_redirects=True, timeout=15.0)

tags_to_test = [
    # Casing / tag formats on womens-handbags
    "coach", "Coach", "COACH",
    "michael-kors", "Michael Kors", "MICHAEL Michael Kors",
    "shoulder-bags", "Shoulder Bags",
    "crossbody-bags", "Crossbody Bags", "crossbody", "Crossbody",
    "totes", "Totes", "tote-bags", "Tote Bags",
    "wallets", "Wallets", "wallets-accessories",
    "backpacks", "Backpacks"
]

print("=== TESTING TAGS ON /collections/womens-handbags/ ===")
for t in tags_to_test:
    url = f"https://therareavenue.com/collections/womens-handbags/{t}"
    r = client.get(url)
    empty = "no products" in r.text.lower() or "there are no products" in r.text.lower()
    print(f"[{r.status_code}] {'EMPTY ' if empty else 'OK    '} /collections/womens-handbags/{t}")
