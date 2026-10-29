import os
import sys
import json
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from scripts.audit_luxury_bags_catalog import get_luxury_bag_products

catalog = get_luxury_bag_products()

for brand in ['coach', 'jwpei', 'michaelkors']:
    print(f"=== FULL DESCRIPTION SAMPLE: {brand.upper()} ===")
    sample = catalog[brand][0]
    print("Title:", sample.get("title"))
    print("Specs:", json.dumps(sample.get("specifications", {}), indent=2))
    d_html = sample.get("description_html") or sample.get("descriptionHtml") or ""
    print("Desc HTML:")
    print(d_html)
    print("-" * 60)
