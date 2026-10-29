import httpx
import json

client = httpx.Client()
# Add a watch with checkcheck and coach pouch
r = client.post("https://therareavenue.com/cart/clear.js")

add_resp = client.post("https://therareavenue.com/cart/add.js", json={
    "items": [
        {
            "id": 57721101779110,
            "quantity": 1,
            "properties": {
                "Certified For": "Tissot Carson Automatic Black Dial Men's Watch T122.407.11.051.00 (40 mm)",
                "_parent_id": "57685641757030"
            }
        },
        {
            "id": 57685641757030,
            "quantity": 1,
            "properties": {
                "Authentication": "CheckCheck Certified (+₹699)",
                "_checkcheck_parent": "true"
            }
        },
        {
            "id": 57685816967526,
            "quantity": 1
        }
    ]
})

cart_resp = client.get("https://therareavenue.com/cart.js")
cart_data = cart_resp.json()

print(f"Total Cart Items: {len(cart_data['items'])}")
for idx, item in enumerate(cart_data['items']):
    print(f"\nItem {idx + 1}:")
    print(f"  Title: {item['title']}")
    print(f"  Variant ID: {item['variant_id']}")
    print(f"  Price: {item['price'] / 100} INR")
    print(f"  Properties: {json.dumps(item['properties'], indent=4)}")
