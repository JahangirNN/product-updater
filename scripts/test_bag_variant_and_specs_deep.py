import os
import sys
import json
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from scripts.audit_luxury_bags_catalog import get_luxury_bag_products
from storage.shopify_taxonomy import prepare_product_set_payload, resolve_options_and_variants

def verify_all_bags():
    catalog = get_luxury_bag_products()
    print("=" * 80)
    print("DEEP VERIFICATION: BAG VARIANT ARCHITECTURE & SPEC ACCORDIONS (1,199 ITEMS)")
    print("=" * 80)

    total_prods = 0
    option_names = set()
    variants_with_files = 0
    total_variants = 0
    issues = []

    for brand, prods in catalog.items():
        print(f"\n--- Checking {brand.upper()} ({len(prods)} products) ---")
        brand_issues = 0
        total_prods += len(prods)

        for p in prods:
            pid = p.get("id") or os.path.basename(p.get("_file_path", "")).replace(".json", "")
            title = p.get("title", "")
            payload = prepare_product_set_payload(p)

            # 1. Option name
            opts = payload.get("productOptions", [])
            if not opts:
                issues.append(f"[{brand}] {pid} has no productOptions")
                brand_issues += 1
            else:
                opt_name = opts[0]["name"]
                option_names.add(opt_name)
                if opt_name == "Option":
                    issues.append(f"[{brand}] {pid} still has generic 'Option' name instead of Color/Size: {title}")
                    brand_issues += 1

            # 2. Variants and image linkages
            vars_list = payload.get("variants", [])
            total_variants += len(vars_list)
            root_files = [f["originalSource"] for f in payload.get("files", [])]

            for v in vars_list:
                v_file = v.get("file")
                if v_file:
                    variants_with_files += 1
                    src = v_file.get("originalSource")
                    if src not in root_files:
                        issues.append(f"[{brand}] {pid} variant file {src} missing from root files payload!")
                        brand_issues += 1

                # Price check (INR whole rupees string e.g. "11414.00")
                price_str = v.get("price", "")
                if not re.match(r"^\d+\.00$", price_str):
                    issues.append(f"[{brand}] {pid} price is not whole rupee INR (.00): '{price_str}'")
                    brand_issues += 1

            # 3. Description HTML and Accordion Quality
            desc_html = payload.get("descriptionHtml", "")
            if not desc_html:
                issues.append(f"[{brand}] {pid} has empty descriptionHtml")
                brand_issues += 1
            else:
                if '<p class="product-summary"></p>' in desc_html:
                    issues.append(f"[{brand}] {pid} has empty product-summary")
                    brand_issues += 1
                if '📏' not in desc_html or 'size-guide-accordion' not in desc_html:
                    issues.append(f"[{brand}] {pid} missing size-guide-accordion")
                    brand_issues += 1
                if '>N/A<' in desc_html or '>None<' in desc_html:
                    issues.append(f"[{brand}] {pid} contains unrendered 'N/A' or 'None' in description specs")
                    brand_issues += 1

        print(f"{brand.upper()}: {len(prods)} products checked, {brand_issues} issues found.")

    print("\n" + "=" * 80)
    print(f"VERIFICATION SUMMARY:")
    print(f"  Total products checked: {total_prods}")
    print(f"  Total variants generated: {total_variants}")
    print(f"  Variants with image files attached: {variants_with_files}")
    print(f"  Observed option names across all products: {option_names}")
    print(f"  Total issues found: {len(issues)}")
    if issues:
        for iss in issues[:20]:
            print("   -", iss)
    else:
        print(">> ALL 1,199 PRODUCTS FULLY COMPLIANT WITH ZERO ISSUES! <<")
    print("=" * 80)
    return len(issues) == 0

if __name__ == "__main__":
    success = verify_all_bags()
    sys.exit(0 if success else 1)
