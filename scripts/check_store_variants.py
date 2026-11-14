import json, glob, os

db_dir = 'product-updater/storage/db'
for store in sorted(os.listdir(db_dir)):
    pdir = os.path.join(db_dir, store, 'products')
    if not os.path.isdir(pdir):
        continue
    sample_files = glob.glob(os.path.join(pdir, '*.json'))[:2]
    print(f"*** STORE: {store} ***")
    for sf in sample_files:
        with open(sf, 'r', encoding='utf-8') as f:
            p = json.load(f)
            vars = p.get('variants', [])
            if vars:
                v = vars[0]
                print(f"  Product: {p.get('title')[:35]}")
                print(f"    v.keys(): {list(v.keys())}")
                print(f"    price={v.get('price')}, current_price={v.get('current_price')}, price_inr={v.get('price_inr')}, source_price={v.get('source_price')}, source_price_usd={v.get('source_price_usd')}")
