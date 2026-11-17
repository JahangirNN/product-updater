import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.forex import get_usd_to_inr_rate
from storage.pricing_engine import resolve_storefront_pricing, get_rule_for_product, load_pricing_rules

def test_katespade_brackets():
    fx = 94.40
    print(f"--- TESTING KATE SPADE PRICING FORMULA (FX={fx}) ---")
    rule = get_rule_for_product("katespade", "Shoulder Bags")
    print(f"Loaded rule for katespade: {rule.get('formula')}")
    assert rule.get("formula") == "price_bracket_markup", f"Expected price_bracket_markup, got {rule.get('formula')}"

    # Bracket 1: Base INR <= 10,000 (e.g., $50 -> ~4,720 INR -> +45% -> ~6,844 -> 6,799)
    p_usd_1 = 50.0
    price_inr_1, _ = resolve_storefront_pricing(p_usd_1, None, "katespade", "Shoulder Bags", fx)
    base_inr_1 = p_usd_1 * fx
    markup_1 = (price_inr_1 - base_inr_1) / base_inr_1
    print(f"Bracket 1: USD ${p_usd_1:.2f} -> Base ₹{base_inr_1:.2f} -> INR ₹{price_inr_1:.2f} (Markup: {markup_1*100:.1f}%)")
    assert base_inr_1 <= 10000
    assert 0.43 <= markup_1 <= 0.47
    assert int(price_inr_1) % 100 == 99

    # Bracket 2: Base INR 10,000 - 15,000 (e.g., $120 -> ~11,328 INR -> +40% -> ~15,859.2 -> 15,899)
    p_usd_2 = 120.0
    price_inr_2, _ = resolve_storefront_pricing(p_usd_2, None, "katespade", "Crossbody Bags", fx)
    base_inr_2 = p_usd_2 * fx
    markup_2 = (price_inr_2 - base_inr_2) / base_inr_2
    print(f"Bracket 2: USD ${p_usd_2:.2f} -> Base ₹{base_inr_2:.2f} -> INR ₹{price_inr_2:.2f} (Markup: {markup_2*100:.1f}%)")
    assert 10000 < base_inr_2 <= 15000
    assert 0.38 <= markup_2 <= 0.42
    assert int(price_inr_2) % 100 == 99

    # Bracket 3: Base INR > 15,000 (e.g., $200 -> ~18,880 INR -> +35% -> ~25,488 -> 25,499)
    p_usd_3 = 200.0
    price_inr_3, _ = resolve_storefront_pricing(p_usd_3, None, "katespade", "Totes & Carryalls", fx)
    base_inr_3 = p_usd_3 * fx
    markup_3 = (price_inr_3 - base_inr_3) / base_inr_3
    print(f"Bracket 3: USD ${p_usd_3:.2f} -> Base ₹{base_inr_3:.2f} -> INR ₹{price_inr_3:.2f} (Markup: {markup_3*100:.1f}%)")
    assert base_inr_3 > 15000
    assert 0.33 <= markup_3 <= 0.37
    assert int(price_inr_3) % 100 == 99

    print("ALL BRACKET ASSERTIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_katespade_brackets()
