import glob
import json
import sys

for brand in ['coach', 'jwpei', 'michaelkors']:
    files = glob.glob(f'storage/db/{brand}/products/*.json')
    brand_broken = 0
    for f in files:
        with open(f, 'r', encoding='utf-8', errors='replace') as fp:
            content = fp.read()
        if '\ufffd' in content:
            brand_broken += 1
    print(f"{brand}: {brand_broken} files contain \\ufffd (replacement character)")
