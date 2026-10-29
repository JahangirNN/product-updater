import urllib.request
import re

urls = [
    'https://therareavenue.com/collections/coach',
    'https://therareavenue.com/collections/men',
    'https://therareavenue.com/collections/women',
    'https://therareavenue.com/collections/all'
]

req_headers = {'User-Agent': 'Mozilla/5.0'}

for u in urls:
    req = urllib.request.Request(u, headers=req_headers)
    try:
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode('utf-8')
            # Find filter parameters in forms or facets
            filter_params = re.findall(r'name=["\'](filter\.[^"\']+)["\']', html)
            filter_labels = re.findall(r'<span class="[^"]*facet[^"]*"[^>]*>([^<]+)</span>', html)
            # Find all filter inputs
            inputs = re.findall(r'<input[^>]*name=["\'](filter\.[^"\']+)["\'][^>]*value=["\']([^"\']+)["\']', html)
            print(f'=== URL: {u} ===')
            print(f'Filter param names: {set(filter_params)}')
            tag_values = [v for k, v in inputs if 'tag' in k]
            vendor_values = [v for k, v in inputs if 'vendor' in k]
            type_values = [v for k, v in inputs if 'type' in k or 'product_type' in k]
            print(f'Available tag filter values ({len(tag_values)}): {tag_values[:10]}')
            print(f'Available vendor filter values ({len(vendor_values)}): {vendor_values[:10]}')
            print(f'Available type filter values ({len(type_values)}): {type_values[:10]}')
            print()
    except Exception as e:
        print(f'URL: {u} -> Error: {e}')
