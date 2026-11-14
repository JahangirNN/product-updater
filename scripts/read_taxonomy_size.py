with open("product-updater/storage/shopify_taxonomy.py", encoding="utf-8") as f:
    text = f.read()

import re
idx = text.find("def extract_variant_size")
if idx != -1:
    print(text[idx:idx+1200])
else:
    print("Not found")
