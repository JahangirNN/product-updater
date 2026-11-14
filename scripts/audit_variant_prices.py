import json, glob, os

db_dir = 'product-updater/storage/db'
store_stats = {}

for store in sorted(os.listdir(db_dir)):
    pdir = os.path.join(db_dir, store, 'products')
    if not os.path.isdir(pdir):
        continue
    store_stats[store] = {
        'total_products': 0,
        'total_variants': 0,
        'variants_missing_inr_price': 0,
        'variants_missing_source_price': 0,
        'variant_keys_found': set(),
        'sample_missing': []
    }
    for pf in glob.glob(os.path.join(pdir, '*.json')):
        with open(pf, 'r', encoding='utf-8') as f:
            p = json.load(f)
            store_stats[store]['total_products'] += 1
            for v in p.get('variants', []):
                store_stats[store]['total_variants'] += 1
                for k in v.keys():
                    store_stats[store]['variant_keys_found'].add(k)
                # Check INR price
                inr = v.get('price') or v.get('current_price') or v.get('price_inr')
                if not inr or float(inr) <= 0:
                    store_stats[store]['variants_missing_inr_price'] += 1
                    if len(store_stats[store]['sample_missing']) < 2:
                        store_stats[store]['sample_missing'].append((p.get('title'), v.get('sku'), v))
                # Check source price
                src_p = v.get('source_price') or v.get('source_price_usd')
                if not src_p or float(src_p) <= 0:
                    store_stats[store]['variants_missing_source_price'] += 1

for st, stt in store_stats.items():
    print(f"=== {st} ===")
    print(f"  Products: {stt['total_products']}, Variants: {stt['total_variants']}")
    print(f"  Missing INR price: {stt['variants_missing_inr_price']}")
    print(f"  Missing Source price: {stt['variants_missing_source_price']}")
    print(f"  Keys found: {sorted(list(stt['variant_keys_found']))}")
    if stt['sample_missing']:
        print(f"  Sample missing: {stt['sample_missing'][0][0]} SKU={stt['sample_missing'][0][1]}")
