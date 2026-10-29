import os
import sys
import json
import re
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from scripts.audit_luxury_bags_catalog import get_luxury_bag_products
from storage.shopify_taxonomy import format_luxury_bag_description_html

catalog = get_luxury_bag_products()

issues = []
for brand, prods in catalog.items():
    for p in prods:
        pid = p.get("id") or p.get("source_sku")
        title = p.get("title", "")
        html = format_luxury_bag_description_html(p)
        
        # Check highlight cards
        mat_match = re.search(r'<div style="font-size: 11px;[^>]*>Material</div>\s*<div[^>]*>([^<]+)</div>', html)
        if mat_match:
            mat_val = mat_match.group(1).strip()
            if mat_val.endswith(" ") or "leather in this" in mat_val.lower() or len(mat_val) < 3:
                issues.append(f"[{brand}] {pid} ({title[:25]}): Bad Material highlight '{mat_val}'")
                
        hw_match = re.search(r'<div style="font-size: 11px;[^>]*>Hardware</div>\s*<div[^>]*>([^<]+)</div>', html)
        if hw_match:
            hw_val = hw_match.group(1).strip()
            if hw_val.endswith(" ") or len(hw_val) < 3:
                issues.append(f"[{brand}] {pid} ({title[:25]}): Bad Hardware highlight '{hw_val}'")
                
        # Check dimension guide
        if "Standard luxury sizing profile" in html:
            # Let's see how many have standard sizing fallback
            pass

print(f"Total highlight issues found: {len(issues)}")
for iss in issues[:20]:
    print("  ", iss)
