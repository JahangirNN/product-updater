import json
import glob

for brand in ['coach', 'jwpei', 'michaelkors']:
    files = glob.glob(f'storage/db/{brand}/products/*.json')
    dropped_variants_total = 0
    multi_dim_products = 0
    for f in files:
        with open(f, 'r', encoding='utf-8') as fp:
            data = json.load(fp)
        vars = data.get('variants', [])
        all_opt_names = []
        for v in vars:
            for ov in v.get('option_values', []):
                on = ov.get('option_name')
                if on and on not in all_opt_names:
                    all_opt_names.append(on)
        if len(all_opt_names) > 1:
            multi_dim_products += 1
            first_vals = [v.get('option_values', [{}])[0].get('name') for v in vars if v.get('option_values')]
            if len(first_vals) != len(set(first_vals)):
                dropped = len(first_vals) - len(set(first_vals))
                dropped_variants_total += dropped
                print(f'[{brand}] {data.get("title")} has {len(vars)} variants, dimensions: {all_opt_names}. Dropped: {dropped}')
    print(f'{brand}: multi_dim_products={multi_dim_products}, dropped_variants_total={dropped_variants_total}')
