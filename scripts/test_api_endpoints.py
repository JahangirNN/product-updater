import requests

key = "u7PNVQx-prod-en-us"
test_urls = [
    f"https://sephora.cnstrc.com/items/P455936?key={key}",
    f"https://sephora.cnstrc.com/v1/item?key={key}&item_id=P455936",
    f"https://sephora.cnstrc.com/v1/variations?key={key}&item_id=P455936",
    "https://www.sephora.com/api/catalog/products/P455936",
    "https://www.sephora.com/api/users/profiles/current/product/P455936",
]

for u in test_urls:
    try:
        r = requests.get(u, timeout=5)
        print(f"Status {r.status_code} for {u}")
        if r.status_code == 200:
            print("Content:", r.text[:200])
    except Exception as e:
        print("Err:", e)
