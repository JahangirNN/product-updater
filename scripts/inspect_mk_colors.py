import glob
import json

mk_files = glob.glob('storage/db/michaelkors/products/*.json')
count = 0
for f in mk_files:
    with open(f, 'r', encoding='utf-8') as fp:
        d = json.load(fp)
    title = d.get('title')
    vars = d.get('variants', [])
    for v in vars:
        ovs = v.get('option_values', [])
        for ov in ovs:
            if ov.get('option_name') == 'Color' and str(ov.get('name')).isdigit():
                count += 1
                if count <= 5:
                    print(f"{title} | SKU: {v.get('sku')} | Color: {ov.get('name')} | URL: {d.get('source_url')}")
print(f"Total MK products with numeric color codes: {count}")
