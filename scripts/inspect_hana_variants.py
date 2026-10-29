import requests

r = requests.get('https://therareavenue.com/products/hana-medium-tote-bag-black-croc.js')
data = r.json()
print('Title:', data.get('title'))
print('Variants count:', len(data.get('variants', [])))
for v in data.get('variants', []):
    print(f"{v['id']} | {v['title']} | price: {v['price']} | compare: {v['compare_at_price']} | avail: {v['available']}")
