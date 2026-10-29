import os
import sys
import json
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from scripts.audit_luxury_bags_catalog import get_luxury_bag_products

catalog = get_luxury_bag_products()

for brand, prods in catalog.items():
    print(f"=== {brand.upper()} ({len(prods)} products) ===")
    opt_combinations = set()
    multi_opts = 0
    single_opts = 0
    zero_opts = 0
    for p in prods:
        vars = p.get("variants", [])
        if not vars:
            zero_opts += 1
            continue
        # collect all option names across variants in this product
        p_opt_names = []
        for v in vars:
            ovs = v.get("option_values", [])
            for ov in ovs:
                on = ov.get("option_name")
                if on and on not in p_opt_names:
                    p_opt_names.append(on)
        p_opt_tuple = tuple(p_opt_names)
        opt_combinations.add(p_opt_tuple)
        if len(p_opt_names) > 1:
            multi_opts += 1
        elif len(p_opt_names) == 1:
            single_opts += 1
        else:
            zero_opts += 1
    print(f"Option combos: {opt_combinations}")
    print(f"Multi-option: {multi_opts}, Single-option: {single_opts}, Zero-option: {zero_opts}")
