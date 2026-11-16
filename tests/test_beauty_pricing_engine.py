import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.pricing_engine import (
    load_pricing_rules,
    get_rule_for_product,
    calculate_storefront_price,
    resolve_usd_bracket_markup,
    apply_charm_rounding
)

def run_tests():
    rules = load_pricing_rules()

    # 1. Rules Loaded
    assert "sephora" in rules["stores"], "Sephora not in stores"
    assert "default" in rules["stores"]["sephora"], "Default not in sephora"
    assert "brands" in rules["stores"]["sephora"], "Brands not in sephora"
    assert "rhode" in rules["stores"]["sephora"]["brands"]
    assert "Haus Labs" in rules["stores"]["sephora"]["brands"]
    assert "MAKEUP BY MARIO" in rules["stores"]["sephora"]["brands"]
    assert "Hourglass" in rules["stores"]["sephora"]["brands"]
    assert "Westman Atelier" in rules["stores"]["sephora"]["brands"]
    print("PASS: test_sephora_rules_loaded")

    # 2. Base Formula
    base_brackets = rules["stores"]["sephora"]["default"]["brackets"]
    assert resolve_usd_bracket_markup(10.0, base_brackets) == 1.00, "Under $20 failed"
    assert resolve_usd_bracket_markup(19.99, base_brackets) == 1.00, "Under $20 (19.99) failed"
    assert resolve_usd_bracket_markup(20.0, base_brackets) == 0.75, "$20 inclusive failed"
    assert resolve_usd_bracket_markup(25.0, base_brackets) == 0.75, "$25 failed"
    assert resolve_usd_bracket_markup(30.0, base_brackets) == 0.75, "$30 inclusive failed"
    assert resolve_usd_bracket_markup(30.01, base_brackets) == 0.55, "$30.01 failed"
    assert resolve_usd_bracket_markup(35.0, base_brackets) == 0.55, "$35 failed"
    assert resolve_usd_bracket_markup(40.0, base_brackets) == 0.55, "$40 inclusive failed"
    assert resolve_usd_bracket_markup(40.01, base_brackets) == 0.40, "$40.01 failed"
    assert resolve_usd_bracket_markup(88.0, base_brackets) == 0.40, "$88 failed"
    print("PASS: test_base_formula_brackets")

    # 3. Rhode Custom
    rhode_brackets = rules["stores"]["sephora"]["brands"]["rhode"]["brackets"]
    assert resolve_usd_bracket_markup(18.0, rhode_brackets) == 0.65
    assert resolve_usd_bracket_markup(24.0, rhode_brackets) == 0.50
    assert resolve_usd_bracket_markup(30.0, rhode_brackets) == 0.50
    assert resolve_usd_bracket_markup(38.0, rhode_brackets) == 0.45
    assert resolve_usd_bracket_markup(45.0, rhode_brackets) == 0.35
    print("PASS: test_rhode_custom_brackets")

    # 4. Haus Labs & Mario
    hl_brackets = rules["stores"]["sephora"]["brands"]["Haus Labs"]["brackets"]
    mario_brackets = rules["stores"]["sephora"]["brands"]["MAKEUP BY MARIO"]["brackets"]
    for b in (hl_brackets, mario_brackets):
        assert resolve_usd_bracket_markup(15.0, b) == 0.85
        assert resolve_usd_bracket_markup(25.0, b) == 0.65
        assert resolve_usd_bracket_markup(35.0, b) == 0.50
        assert resolve_usd_bracket_markup(45.0, b) == 0.40
    print("PASS: test_haus_labs_and_mario_brackets")

    # 5. Hourglass & Westman Atelier
    hg_brackets = rules["stores"]["sephora"]["brands"]["Hourglass"]["brackets"]
    wa_brackets = rules["stores"]["sephora"]["brands"]["Westman Atelier"]["brackets"]
    for b in (hg_brackets, wa_brackets):
        assert resolve_usd_bracket_markup(15.0, b) == 0.80
        assert resolve_usd_bracket_markup(25.0, b) == 0.60
        assert resolve_usd_bracket_markup(35.0, b) == 0.45
        assert resolve_usd_bracket_markup(68.0, b) == 0.35
    print("PASS: test_hourglass_and_westman_brackets")

    # 6. Storefront Charm Price Calculation
    fx = 93.85
    p_rhode = calculate_storefront_price(18.0, "sephora", "", fx, rules=rules, vendor="rhode")
    assert p_rhode == 2799.0, f"Expected 2799.0, got {p_rhode}"

    p_sf = calculate_storefront_price(24.0, "sephora", "", fx, rules=rules, vendor="Summer Fridays")
    assert p_sf % 100 == 99.0

    p_saie = calculate_storefront_price(25.0, "sephora", "", fx, rules=rules, vendor="Saie")
    assert p_saie == 4099.0, f"Expected 4099.0, got {p_saie}"

    p_hg = calculate_storefront_price(98.0, "sephora", "", fx, rules=rules, vendor="Hourglass")
    assert p_hg == 12399.0, f"Expected 12399.0, got {p_hg}"
    print("PASS: test_storefront_price_charm_calculation")

    print("\nALL 6 TEST SUITES PASSED PERFECTLY!")

if __name__ == "__main__":
    run_tests()
