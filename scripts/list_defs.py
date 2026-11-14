with open("product-updater/storage/shopify_taxonomy.py", encoding="utf-8") as f:
    for idx, line in enumerate(f):
        if line.startswith("def "):
            print(f"{idx+1}: {line.strip()}")
