with open("product-updater/storage/shopify_taxonomy.py", encoding="utf-8") as f:
    text = f.read()

idx = text.find("def prepare_product_set_payload")
if idx != -1:
    print(text[idx+500:idx+1500])
