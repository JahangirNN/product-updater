import os
import sys
import glob
import json
from collections import Counter, defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

COACH_DIR = os.path.join(PROJECT_ROOT, "storage", "db", "coach", "products")
JWPEI_DIR = os.path.join(PROJECT_ROOT, "storage", "db", "jwpei", "products")
MK_DIR = os.path.join(PROJECT_ROOT, "storage", "db", "michaelkors", "products")

from scripts.audit_luxury_bags_catalog import get_luxury_bag_products
from storage.shopify_taxonomy import resolve_options_and_variants, resolve_product_type, resolve_luxury_bag_silhouette

def analyze():
    catalog = get_luxury_bag_products()
    
    print("=" * 80)
    print("DEEP AUDIT: VARIANT & SPECIFICATION STRUCTURE FOR LUXURY BAGS")
    print("=" * 80)

    for brand, prods in catalog.items():
        print(f"\n--- {brand.upper()} ({len(prods)} products) ---")
        
        variant_counts = Counter()
        has_color = 0
        has_size = 0
        multi_variants = 0
        spec_keys_counter = Counter()
        sample_variants = []
        sample_specs = []
        
        for p in prods:
            vars_list = p.get("variants") or []
            v_len = len(vars_list)
            variant_counts[v_len] += 1
            if v_len > 1:
                multi_variants += 1
            
            c_found = False
            s_found = False
            for v in vars_list:
                if v.get("color"):
                    c_found = True
                if v.get("size"):
                    s_found = True
            if c_found:
                has_color += 1
            if s_found:
                has_size += 1
                
            specs = p.get("specifications") or {}
            for k in specs.keys():
                spec_keys_counter[k] += 1
                
            if len(sample_variants) < 3 and v_len > 0:
                sample_variants.append((p.get("title"), vars_list))
            if len(sample_specs) < 3 and specs:
                sample_specs.append((p.get("title"), specs, (p.get("description_html") or p.get("descriptionHtml") or "")[:200]))

        print(f"Variant count distribution: {dict(sorted(variant_counts.items()))}")
        print(f"Products with >1 variant: {multi_variants}/{len(prods)}")
        print(f"Products with color: {has_color}/{len(prods)}")
        print(f"Products with size: {has_size}/{len(prods)}")
        print(f"Top 10 Specification keys: {spec_keys_counter.most_common(10)}")
        
        print("\nSample Product Variants:")
        for title, vlist in sample_variants:
            print(f"  Title: {title}")
            print(f"    Variants ({len(vlist)}): {json.dumps(vlist[:2], indent=6)}")
            
        print("\nSample Product Specs & Description HTML:")
        for title, specs, dhtml in sample_specs:
            print(f"  Title: {title}")
            print(f"    Specs: {json.dumps(specs, indent=6)}")
            print(f"    Desc HTML snippet: {dhtml}")

if __name__ == "__main__":
    analyze()
