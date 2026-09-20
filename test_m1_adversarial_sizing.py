"""
Milestone 1 Adversarial Challenge & Verification Test Suite: Sizing & Math
Challenger 1 (Milestone 1) - Empirical Verification Harness

Empirically challenges:
1. Sizing collision boundaries (Toddler 7C vs Big Kids 7.0Y vs Adult 7.0 M vs Adult 7.0 W)
2. Substring token false-positives (LTD -> Toddler, Straps -> Preschool, Wings -> Grade School)
3. Raw size dictionary inspection bugs (in_stock containing "c" -> Toddler)
4. Fractional size parsing & table conversions (10.5C, 13.5C, 3.5Y, 6.5M)
5. Extreme sizing boundary conditions (Infant 1C/2C, Youth 7.0Y, Adult 15.0M-18.0M)
6. Whole-rupee math & zero-paise invariants across floating-point USD and forex rates
7. Size conversion table HTML validity & tag balancing
8. Preschool size sorting sequence (10.5C-13.5C vs 1.0Y-3.0Y)
"""
import os
import sys
import re
import html
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stores.jdsports.inflow import (
    classify_sizing_category,
    determine_gender,
    parse_and_format_size,
    generate_description_html,
    parse_product_payload,
    NIKE_MEN_US_TO_UK,
    NIKE_MEN_US_TO_EU,
    NIKE_WOMEN_US_TO_UK,
    NIKE_WOMEN_US_TO_EU,
    NIKE_GS_US_TO_UK,
    NIKE_GS_US_TO_EU,
    NIKE_PS_US_TO_UK,
    NIKE_PS_US_TO_EU,
    NIKE_TD_US_TO_UK,
    NIKE_TD_US_TO_EU
)
from stores.jdsports.delta import apply_delta_to_product

class StrictHTMLValidator(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack: List[str] = []
        self.errors: List[str] = []
        self.void_tags = {'br', 'hr', 'img', 'input', 'meta', 'link'}

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        if tag.lower() not in self.void_tags:
            self.stack.append(tag.lower())

    def handle_endtag(self, tag: str):
        t = tag.lower()
        if t in self.void_tags:
            return
        if not self.stack:
            self.errors.append(f"Unexpected end tag: </{t}> without matching open tag")
        elif self.stack[-1] == t:
            self.stack.pop()
        else:
            self.errors.append(f"Mismatched tag: expected </{self.stack[-1]}>, got </{t}>")

def run_tests():
    total_tests = 0
    passed_tests = 0
    failures: List[Dict[str, Any]] = []

    def check(name: str, condition: bool, details: str = ""):
        nonlocal total_tests, passed_tests
        total_tests += 1
        if condition:
            passed_tests += 1
            print(f"  [PASS] {name}")
        else:
            print(f"  [FAIL] {name} - {details}")
            failures.append({"name": name, "details": details})

    print("=" * 80)
    print("SUITE 1: SIZING COLLISION BOUNDARIES (7C vs 7.0Y vs 7.0 M vs 7.0 W)")
    print("=" * 80)

    # 1.1 Four-tier 7.0 collision disambiguation
    t_lbl, t_uk, t_eu, t_val = parse_and_format_size("7.0", "Toddler", "Unisex")
    check("Toddler 7.0 -> US 7C label", t_lbl == "US 7C", f"Got '{t_lbl}'")
    check("Toddler 7.0 -> UK 6.5", t_uk == "6.5", f"Got '{t_uk}'")
    check("Toddler 7.0 -> EU 23.5", t_eu == "23.5", f"Got '{t_eu}'")

    gs_lbl, gs_uk, gs_eu, gs_val = parse_and_format_size("7.0", "Grade School", "Unisex")
    check("Grade School 7.0 -> US 7.0Y label", gs_lbl == "US 7.0Y", f"Got '{gs_lbl}'")
    check("Grade School 7.0 -> UK 6", gs_uk == "6", f"Got '{gs_uk}'")
    check("Grade School 7.0 -> EU 40", gs_eu == "40", f"Got '{gs_eu}'")

    am_lbl, am_uk, am_eu, am_val = parse_and_format_size("7.0", "Adult", "Men's")
    check("Adult Men's 7.0 -> US 7.0 label", am_lbl == "US 7.0", f"Got '{am_lbl}'")
    check("Adult Men's 7.0 -> UK 6", am_uk == "6", f"Got '{am_uk}'")
    check("Adult Men's 7.0 -> EU 40", am_eu == "40", f"Got '{am_eu}'")

    aw_lbl, aw_uk, aw_eu, aw_val = parse_and_format_size("7.0", "Adult", "Women's")
    check("Adult Women's 7.0 -> US 7.0 label", aw_lbl == "US 7.0", f"Got '{aw_lbl}'")
    check("Adult Women's 7.0 -> UK 4.5", aw_uk == "4.5", f"Got '{aw_uk}'")
    check("Adult Women's 7.0 -> EU 38", aw_eu == "38", f"Got '{aw_eu}'")

    # Verify distinct labels prevent cross-tier collisions
    labels = {t_lbl, gs_lbl, am_lbl}
    check("Toddler, Youth, and Adult Men's labels are mutually distinct", len(labels) == 3, f"Labels: {labels}")

    # 1.2 Substring token false-positive tests in classification
    cat_ltd = classify_sizing_category("Men's Nike Air Max LTD 3 Casual Shoes")
    check("Title 'Men's Nike Air Max LTD 3' must NOT classify as Toddler (word boundary on 'td')",
          cat_ltd == "Adult", f"Got '{cat_ltd}' instead of Adult due to 'td' in 'ltd'")

    cat_straps = classify_sizing_category("Men's Nike Air Force 1 High with Straps")
    check("Title 'Nike Air Force 1 with Straps' must NOT classify as Preschool (word boundary on 'ps')",
          cat_straps == "Adult", f"Got '{cat_straps}' instead of Adult due to 'ps' in 'straps'")

    cat_wings = classify_sizing_category("Men's Nike Air Max Wings Casual Shoes")
    check("Title 'Nike Air Max Wings' must NOT classify as Grade School (word boundary on 'gs')",
          cat_wings == "Adult", f"Got '{cat_wings}' instead of Adult due to 'gs' in 'wings'")

    # 1.3 Raw sizes inspection bug when sizes are dicts
    size_dicts = [{"size": "10.0", "in_stock": True}, {"size": "11.0", "in_stock": True}]
    cat_dict = classify_sizing_category("Nike Air Zoom Pegasus", raw_sizes=size_dicts)
    check("raw_sizes with [{'size':'10.0', 'in_stock':True}] must NOT classify as Toddler",
          cat_dict == "Adult", f"Got '{cat_dict}' instead of Adult because 'in_stock' contains letter 'c'")

    print("\n" + "=" * 80)
    print("SUITE 2: FRACTIONAL SIZES (10.5C, 13.5C, 3.5Y, 6.5M)")
    print("=" * 80)

    # 2.1 Preschool fractional boundaries
    ps105_lbl, ps105_uk, ps105_eu, _ = parse_and_format_size("10.5C", "Preschool")
    check("Preschool 10.5C -> US 10.5C", ps105_lbl == "US 10.5C", f"Got '{ps105_lbl}'")
    check("Preschool 10.5C -> UK 10", ps105_uk == "10", f"Got '{ps105_uk}'")
    check("Preschool 10.5C -> EU 27.5", ps105_eu == "27.5", f"Got '{ps105_eu}'")

    ps135_lbl, ps135_uk, ps135_eu, _ = parse_and_format_size("13.5C", "Preschool")
    check("Preschool 13.5C -> US 13.5C", ps135_lbl == "US 13.5C", f"Got '{ps135_lbl}'")
    check("Preschool 13.5C -> UK 13", ps135_uk == "13", f"Got '{ps135_uk}'")
    check("Preschool 13.5C -> EU 31.5", ps135_eu == "31.5", f"Got '{ps135_eu}'")

    # 2.2 Grade School fractional boundaries
    gs35_lbl, gs35_uk, gs35_eu, _ = parse_and_format_size("3.5Y", "Grade School")
    check("Grade School 3.5Y -> US 3.5Y", gs35_lbl == "US 3.5Y", f"Got '{gs35_lbl}'")
    check("Grade School 3.5Y -> UK 3", gs35_uk == "3", f"Got '{gs35_uk}'")
    check("Grade School 3.5Y -> EU 35.5", gs35_eu == "35.5", f"Got '{gs35_eu}'")

    # 2.3 Adult Men's fractional boundaries
    am65_lbl, am65_uk, am65_eu, _ = parse_and_format_size("6.5M", "Adult", "Men's")
    check("Adult Men's 6.5M -> US 6.5", am65_lbl == "US 6.5", f"Got '{am65_lbl}'")
    check("Adult Men's 6.5M -> UK 6", am65_uk == "6", f"Got '{am65_uk}'")
    check("Adult Men's 6.5M -> EU 39", am65_eu == "39", f"Got '{am65_eu}'")

    # 2.4 Adult Women's fractional boundaries
    aw75_lbl, aw75_uk, aw75_eu, _ = parse_and_format_size("7.5", "Adult", "Women's")
    check("Adult Women's 7.5 -> US 7.5", aw75_lbl == "US 7.5", f"Got '{aw75_lbl}'")
    check("Adult Women's 7.5 -> UK 5", aw75_uk == "5", f"Got '{aw75_uk}'")
    check("Adult Women's 7.5 -> EU 38.5", aw75_eu == "38.5", f"Got '{aw75_eu}'")

    # 2.5 Dual Unisex sizing handling (e.g. M 7.0 / W 8.5)
    dual_lbl, dual_uk, dual_eu, dual_val = parse_and_format_size("M 7.0 / W 8.5", "Adult", "Unisex")
    check("Dual size 'M 7.0 / W 8.5' parses numeric value > 0 without corrupting to 7.08.5",
          dual_val > 0.0 and dual_lbl != "US 7.08.5",
          f"Got label '{dual_lbl}', numeric {dual_val} (collapsed concatenated numbers)")

    print("\n" + "=" * 80)
    print("SUITE 3: EXTREME SIZES & BOUNDARY CONDITIONS (1C/2C, 7.0Y, 15.0M-18.0M)")
    print("=" * 80)

    # 3.1 Lowest Infant Sizes
    td1_lbl, td1_uk, td1_eu, td1_val = parse_and_format_size("1C", "Toddler")
    check("Infant 1C -> US 1C", td1_lbl == "US 1C", f"Got '{td1_lbl}'")
    check("Infant 1C -> UK 0.5", td1_uk == "0.5", f"Got '{td1_uk}'")
    check("Infant 1C -> EU 16", td1_eu == "16", f"Got '{td1_eu}'")

    td2_lbl, td2_uk, td2_eu, td2_val = parse_and_format_size("2C", "Toddler")
    check("Infant 2C -> US 2C", td2_lbl == "US 2C", f"Got '{td2_lbl}'")
    check("Infant 2C -> UK 1.5", td2_uk == "1.5", f"Got '{td2_uk}'")
    check("Infant 2C -> EU 17", td2_eu == "17", f"Got '{td2_eu}'")

    # 3.2 Youth 7.0Y upper bound
    gs7_lbl, gs7_uk, gs7_eu, gs7_val = parse_and_format_size("7.0Y", "Grade School")
    check("Youth 7.0Y -> US 7.0Y", gs7_lbl == "US 7.0Y", f"Got '{gs7_lbl}'")
    check("Youth 7.0Y -> UK 6", gs7_uk == "6", f"Got '{gs7_uk}'")
    check("Youth 7.0Y -> EU 40", gs7_eu == "40", f"Got '{gs7_eu}'")

    # 3.3 Large Adult Sizes
    am15_lbl, am15_uk, am15_eu, am15_val = parse_and_format_size("15.0M", "Adult", "Men's")
    check("Adult 15.0M -> US 15.0", am15_lbl == "US 15.0", f"Got '{am15_lbl}'")
    check("Adult 15.0M -> UK 14", am15_uk == "14", f"Got '{am15_uk}'")
    check("Adult 15.0M -> EU 49.5", am15_eu == "49.5", f"Got '{am15_eu}'")

    am16_lbl, am16_uk, am16_eu, am16_val = parse_and_format_size("16.0", "Adult", "Men's")
    check("Adult 16.0M -> US 16.0", am16_lbl == "US 16.0", f"Got '{am16_lbl}'")
    check("Adult 16.0M -> non-empty fallback UK", bool(am16_uk), f"Got '{am16_uk}'")
    check("Adult 16.0M -> non-empty fallback EU", bool(am16_eu), f"Got '{am16_eu}'")

    am18_lbl, am18_uk, am18_eu, am18_val = parse_and_format_size("18.0", "Adult", "Men's")
    check("Adult 18.0M -> US 18.0", am18_lbl == "US 18.0", f"Got '{am18_lbl}'")

    # 3.4 Women's extended sizes
    aw12_lbl, aw12_uk, aw12_eu, aw12_val = parse_and_format_size("12.0", "Adult", "Women's")
    check("Women's 12.0 -> US 12.0", aw12_lbl == "US 12.0", f"Got '{aw12_lbl}'")
    check("Women's 12.0 -> UK 9.5", aw12_uk == "9.5", f"Got '{aw12_uk}'")
    check("Women's 12.0 -> EU 44.5", aw12_eu == "44.5", f"Got '{aw12_eu}'")

    print("\n" + "=" * 80)
    print("SUITE 4: WHOLE-RUPEE MATH (ZERO PAISE INVARIANT)")
    print("=" * 80)

    test_prices = [190.00, 112.50, 44.99, 0.99, 99.95, 150.333333]
    test_rates = [84.15, 83.92, 86.425, 90.12345]

    all_inflow_inr_integers = True
    for p in test_prices:
        for r in test_rates:
            raw_payload = {
                "@type": "Product",
                "name": "Nike Air Force 1 '07",
                "source_price": p,
                "source_compare_at_price": p * 1.25,
                "sizes": ["8.0", "9.0", "10.0"]
            }
            parsed = parse_product_payload(raw_payload, usd_to_inr_rate=r)
            if not parsed["current_price"].is_integer():
                all_inflow_inr_integers = False
            if parsed["compare_at_price"] and not parsed["compare_at_price"].is_integer():
                all_inflow_inr_integers = False
            for v in parsed["variants"]:
                if not float(v["price"]).is_integer():
                    all_inflow_inr_integers = False
                if v["compare_at_price"] and not float(v["compare_at_price"]).is_integer():
                    all_inflow_inr_integers = False

    check("Inflow: 100% parent and variant INR prices have zero fractional paise", all_inflow_inr_integers)

    # Test delta update whole-rupee math & parent-variant price sync
    base_prod = parse_product_payload({
        "@type": "Product",
        "name": "Nike Air Max 90",
        "source_price": 100.0,
        "sizes": ["8.0", "9.0"]
    }, usd_to_inr_rate=84.15)

    delta_price_shift = {
        "status": "success",
        "price_changed": True,
        "current_source_price": 112.50,
        "current_compare_price": 140.25,
        "availability": "in_stock"
    }
    updated_prod, changed = apply_delta_to_product(base_prod, delta_price_shift, forex_rate=84.15)
    check("Delta update: parent current_price is whole integer INR",
          updated_prod["current_price"].is_integer(), f"Got {updated_prod['current_price']}")
    check("Delta update: parent compare_at_price is whole integer INR",
          updated_prod["compare_at_price"].is_integer(), f"Got {updated_prod['compare_at_price']}")

    # Check parent-variant price synchronization when variants_delta is omitted
    variant_prices_synced = True
    expected_var_inr = float(round(112.50 * 84.15))
    for v in updated_prod["variants"]:
        if float(v["price"]) != expected_var_inr:
            variant_prices_synced = False
    check("Delta update: child variant prices sync with parent price on top-level shift",
          variant_prices_synced,
          f"Variants kept old price {updated_prod['variants'][0]['price']} instead of updated {expected_var_inr:.2f}")

    print("\n" + "=" * 80)
    print("SUITE 5: SIZING ACCORDION HTML TABLE VALIDITY")
    print("=" * 80)

    specs_sample = {
        "Brand": "Nike",
        "Model": "Air Max 90",
        "Color": "White/Black",
        "Manufacturer SKU": "CW4555-002"
    }
    sizes_sample = [
        {"size_label": "US 7.0", "uk_str": "6", "eu_str": "40", "in_stock": True},
        {"size_label": "US 8.0", "uk_str": "7", "eu_str": "41", "in_stock": False},
        {"size_label": "US 9.0", "uk_str": "8", "eu_str": "42.5", "in_stock": True}
    ]

    html_out = generate_description_html("Nike Air Max 90", "<p>Great shoe</p>", "Adult", "Men's", specs_sample, sizes_sample)

    validator = StrictHTMLValidator()
    validator.feed(html_out)
    check("HTML accordion has no unclosed tags", len(validator.stack) == 0, f"Unclosed tags: {validator.stack}")
    check("HTML accordion has no mismatched tags", len(validator.errors) == 0, f"Errors: {validator.errors}")
    check("HTML contains <details class='size-guide-accordion'>", "<details class=\"size-guide-accordion\"" in html_out)
    check("HTML contains <table> with headers", ">US Size</th>" in html_out and ">UK Size</th>" in html_out)
    check("HTML contains all size rows", ">US 7.0</td>" in html_out and ">US 8.0</td>" in html_out)

    # Empty sizes test
    empty_html = generate_description_html("Nike Air Max 90", "", "Adult", "Men's", specs_sample, [])
    empty_val = StrictHTMLValidator()
    empty_val.feed(empty_html)
    check("HTML accordion with empty sizes list generates valid balanced HTML", len(empty_val.stack) == 0 and len(empty_val.errors) == 0)

    print("\n" + "=" * 80)
    print("SUITE 6: PRESCHOOL SIZING SEQUENCE ORDERING")
    print("=" * 80)

    # In Nike Preschool (10.5C – 3.0Y):
    # Progression: 10.5C -> 11C -> 12C -> 13C -> 1.0Y -> 2.0Y -> 3.0Y
    ps_raw = {
        "@type": "ProductGroup",
        "name": "Nike Air Max 90 Little Kids Preschool Shoes",
        "hasVariant": [
            {"size": "10.5", "in_stock": True, "sku": "SKU-105"},
            {"size": "11.0", "in_stock": True, "sku": "SKU-110"},
            {"size": "12.0", "in_stock": True, "sku": "SKU-120"},
            {"size": "13.0", "in_stock": True, "sku": "SKU-130"},
            {"size": "1.0", "in_stock": True, "sku": "SKU-10Y"},
            {"size": "2.0", "in_stock": True, "sku": "SKU-20Y"},
            {"size": "3.0", "in_stock": True, "sku": "SKU-30Y"}
        ]
    }
    ps_prod = parse_product_payload(ps_raw)
    ordered_labels = [v["option_values"][0]["name"] for v in ps_prod["variants"]]
    idx_105c = ordered_labels.index("US 10.5C") if "US 10.5C" in ordered_labels else -1
    idx_10y = ordered_labels.index("US 1.0Y") if "US 1.0Y" in ordered_labels else -1

    check("Preschool sequence places US 10.5C BEFORE US 1.0Y in foot length progression",
          idx_105c >= 0 and idx_10y >= 0 and idx_105c < idx_10y,
          f"US 1.0Y (idx {idx_10y}) appeared before US 10.5C (idx {idx_105c}) due to raw numeric sorting: {ordered_labels}")

    print("\n" + "=" * 80)
    print(f"RESULTS SUMMARY: {passed_tests} / {total_tests} tests passed ({(passed_tests/total_tests)*100:.1f}%)")
    print(f"FAILURES COUNT: {len(failures)}")
    print("=" * 80)
    for f in failures:
        print(f"  ❌ {f['name']}: {f['details']}")

    return passed_tests, total_tests, failures

if __name__ == "__main__":
    passed, total, fails = run_tests()
    sys.exit(0 if len(fails) == 0 else 1)
