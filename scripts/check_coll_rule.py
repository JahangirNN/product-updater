with open("product-updater/storage/shopify_collections.py", encoding="utf-8") as f:
    text = f.read()

idx = text.find('"handle": "beauty"')
if idx != -1:
    print(text[idx-50:idx+600])
else:
    print("beauty handle not found in collections manifest")
