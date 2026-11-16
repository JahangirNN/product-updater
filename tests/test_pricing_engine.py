"""
Comprehensive Unit & Integration Test Suite for Decoupled Storefront Pricing Engine
Adheres to ADR 0005, ADR 0006, and ADR 0028.
Verifies:
1. Mathematical precision of JW PEI linear markup & charm rounding formulas.
2. Individual variant pricing resolution for products with price-differentiated variants.
3. Zero Database Mutation Invariant (disk JSON files remain 100% unaltered).
4. Compare-at price validation (suppression of equal/inverted discounts).
5. Global default fallback resilience for unconfigured stores.
6. Integration with Shopify payload generation and delta event logging.
"""
import os
import sys
import json
import glob
import unittest
import copy
from decimal import Decimal

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.pricing_engine import (
    commercial_round_half_up,
    apply_charm_rounding,
    apply_pricing_formula,
    get_rule_for_product,
    calculate_storefront_price,
    resolve_storefront_pricing,
    resolve_product_storefront_pricing,
    resolve_bracket_markup,
    resolve_price_bracket_markup,
    DEFAULT_DISCOUNT_BRACKETS,
    GLOBAL_DEFAULT_RULE
)
from storage.shopify_taxonomy import (
    resolve_options_and_variants,
    prepare_product_set_payload,
    resolve_product_type
)


class TestCommercialRoundingAndCharm(unittest.TestCase):
    """Test commercial round-half-up and charm ending behavior."""

    def test_commercial_round_half_up_thresholds(self):
        # Commercial round: >= 50 rounds up to 100
        self.assertEqual(commercial_round_half_up(150.0, 100), 200)
        self.assertEqual(commercial_round_half_up(149.99, 100), 100)
        self.assertEqual(commercial_round_half_up(100.0, 100), 100)
        self.assertEqual(commercial_round_half_up(50.0, 100), 100)
        self.assertEqual(commercial_round_half_up(49.9, 100), 0)

    def test_commercial_round_zero_and_negative(self):
        self.assertEqual(commercial_round_half_up(0.0, 100), 0)
        self.assertEqual(commercial_round_half_up(-50.0, 100), 0)

    def test_charm_rounding_ends_in_99(self):
        # Values rounded to nearest 100 with charm_offset -1 must end in 99
        test_values = [11321.0, 13481.0, 7001.0, 15641.0, 26634.0]
        for val in test_values:
            charmed = apply_charm_rounding(val, nearest=100, charm_offset=-1)
            self.assertEqual(int(charmed) % 100, 99, f"Value {val} charmed to {charmed} did not end in 99")

    def test_charm_rounding_zero_guard(self):
        self.assertEqual(apply_charm_rounding(0.0, nearest=100, charm_offset=-1), 0.0)
        self.assertEqual(apply_charm_rounding(-10.0, nearest=100, charm_offset=-1), 0.0)


class TestJWPEIPricingFormulas(unittest.TestCase):
    """Verify JW PEI pricing formula mathematical equivalence and accuracy."""

    def setUp(self):
        self.forex_rate = 94.0
        self.rule = {
            "formula": "linear_markup",
            "base_usd": 89.0,
            "base_markup_inr": 2955.0,
            "per_usd_markup_inr": 14.0,
            "fx_addon": 14.0,
            "fixed_offset_inr": 1709.0,
            "round_nearest": 100,
            "charm_offset": -1
        }

    def test_formula_mathematical_equivalence(self):
        """
        Verify that:
        Raw A = Source USD * Live FX + [2955 + (Source USD - 89) * 14]
        Raw B = Source USD * (Live FX + 14) + 1709
        are identical for various price points.
        """
        test_prices = [39.0, 59.0, 89.0, 99.0, 109.0, 129.0, 159.0, 229.0]
        for usd in test_prices:
            raw_a = (usd * self.forex_rate) + (2955.0 + (usd - 89.0) * 14.0)
            raw_b = usd * (self.forex_rate + 14.0) + 1709.0
            self.assertAlmostEqual(raw_a, raw_b, places=4, msg=f"Formulas diverged at USD ${usd}")

            final_a = apply_charm_rounding(raw_a, 100, -1)
            final_b = apply_charm_rounding(raw_b, 100, -1)
            self.assertEqual(final_a, final_b)
            self.assertEqual(int(final_a) % 100, 99)

    def test_base_price_89_exact_value(self):
        # For $89 at FX 90.0:
        # 89 * 104 + 1709 = 9256 + 1709 = 10965 -> round: 11000 - 1 = 10999
        price = apply_pricing_formula(89.0, self.rule, 90.0)
        self.assertEqual(price, 10999.0)

    def test_base_price_109_exact_value(self):
        # For $109 at FX 90.0:
        # 109 * 104 + 1709 = 11336 + 1709 = 13045 -> round: 13000 - 1 = 12999
        price = apply_pricing_formula(109.0, self.rule, 90.0)
        self.assertEqual(price, 12999.0)


class TestCompareAtPriceResolution(unittest.TestCase):
    """Test resolution of compare-at prices and defensive guards."""

    def test_valid_discount_resolution(self):
        # Selling price: $89, Compare at: $119
        p_inr, comp_inr = resolve_storefront_pricing(89.0, 119.0, "jwpei", "Shoulder Bags", 90.0)
        self.assertEqual(p_inr, 10999.0)
        self.assertEqual(comp_inr, 14099.0)
        self.assertGreater(comp_inr, p_inr)

    def test_equal_compare_at_suppressed(self):
        # When compare price equals source price, compare_at must be None
        p_inr, comp_inr = resolve_storefront_pricing(89.0, 89.0, "jwpei", "Shoulder Bags", 90.0)
        self.assertEqual(p_inr, 10999.0)
        self.assertIsNone(comp_inr)

    def test_inverted_compare_at_suppressed(self):
        # When compare price is lower than source price, compare_at must be None
        p_inr, comp_inr = resolve_storefront_pricing(89.0, 79.0, "jwpei", "Shoulder Bags", 90.0)
        self.assertEqual(p_inr, 10999.0)
        self.assertIsNone(comp_inr)

    def test_none_compare_at(self):
        p_inr, comp_inr = resolve_storefront_pricing(89.0, None, "jwpei", "Shoulder Bags", 90.0)
        self.assertEqual(p_inr, 10999.0)
        self.assertIsNone(comp_inr)


class TestGlobalDefaultAndStoreResolution(unittest.TestCase):
    """Verify fallback behavior for unconfigured stores and categories with universal .99 charm rounding."""

    def test_unconfigured_store_uses_standard_forex(self):
        # Unconfigured store e.g. "footlocker" with $200 at FX 90.0 -> 17999.0
        p_inr, comp_inr = resolve_storefront_pricing(200.0, 250.0, "footlocker", "Shoulder Bags", 90.0)
        self.assertEqual(p_inr, 17999.0)
        self.assertEqual(comp_inr, 22499.0)
        self.assertEqual(int(p_inr) % 100, 99)
        self.assertEqual(int(comp_inr) % 100, 99)

    def test_unknown_store_slug(self):
        p_inr, comp_inr = resolve_storefront_pricing(100.0, None, "unknown_boutique", "Shoes", 92.0)
        self.assertEqual(p_inr, 9199.0)
        self.assertEqual(int(p_inr) % 100, 99)
        self.assertIsNone(comp_inr)

    def test_global_default_produces_charm_99(self):
        """Sample product $419 USD at FX 96.0 must produce ₹40,199.0 (ADR 0028)."""
        # 419 * 96.0 = 40224.0 -> commercial_round_half_up(40224, 100) = 40200 -> 40200 - 1 = 40199.0
        p_inr, _ = resolve_storefront_pricing(419.0, None, "nordstrom", "Shoes", 96.0)
        self.assertEqual(p_inr, 40199.0)
        self.assertEqual(int(p_inr) % 100, 99)


class TestVariantPricingDifferentiation(unittest.TestCase):
    """Verify variants with distinct USD prices receive individual INR storefront prices."""

    def test_multi_price_variants_in_options_and_variants(self):
        mock_prod = {
            "source_store": "jwpei",
            "title": "Multi Price Test Bag",
            "source_price": 99.0,
            "variants": [
                {
                    "sku": "TEST-VAR-1",
                    "title": "Small / Black",
                    "source_price": 99.0,
                    "in_stock": True,
                    "option_values": [{"option_name": "Color", "name": "Black"}]
                },
                {
                    "sku": "TEST-VAR-2",
                    "title": "Medium / Brown",
                    "source_price": 129.0,
                    "in_stock": True,
                    "option_values": [{"option_name": "Color", "name": "Brown"}]
                },
                {
                    "sku": "TEST-VAR-3",
                    "title": "Large / Burgundy",
                    "source_price": 159.0,
                    "in_stock": True,
                    "option_values": [{"option_name": "Color", "name": "Burgundy"}]
                }
            ]
        }

        forex_rate = 90.0
        opts, variants = resolve_options_and_variants(mock_prod, forex_rate, 99.0, None)

        self.assertEqual(len(variants), 3)
        prices = [float(v["price"]) for v in variants]
        # $99 at FX 90 -> 99 * 104 + 1709 = 12005 -> 12000 - 1 = 11999
        # $129 at FX 90 -> 129 * 104 + 1709 = 15125 -> 15100 - 1 = 15099
        # $159 at FX 90 -> 159 * 104 + 1709 = 18245 -> 18200 - 1 = 18199
        self.assertEqual(prices[0], 11999.0)
        self.assertEqual(prices[1], 15099.0)
        self.assertEqual(prices[2], 18199.0)

        # All variants must have charm pricing ending in 99
        for p in prices:
            self.assertEqual(int(p) % 100, 99)

    def test_oos_price_floor_clamping(self):
        """OOS variant cheaper than in-stock variant is clamped to min in-stock price."""
        mock_prod = {
            "source_store": "jwpei",
            "title": "OOS Floor Test Bag",
            "source_price": 129.0,
            "variants": [
                {
                    "sku": "TEST-IN-STOCK",
                    "title": "In Stock Color",
                    "source_price": 129.0,
                    "in_stock": True,
                    "option_values": [{"option_name": "Color", "name": "In Stock Color"}]
                },
                {
                    "sku": "TEST-OOS-CHEAPER",
                    "title": "OOS Cheaper Color",
                    "source_price": 79.0,
                    "in_stock": False,
                    "option_values": [{"option_name": "Color", "name": "OOS Cheaper Color"}]
                }
            ]
        }

        forex_rate = 90.0
        opts, variants = resolve_options_and_variants(mock_prod, forex_rate, 129.0, None)
        v_instock = next(v for v in variants if "TEST-IN-STOCK" in v["sku"])
        v_oos = next(v for v in variants if "TEST-OOS-CHEAPER" in v["sku"])

        # OOS variant must be clamped to the in-stock variant's price
        self.assertEqual(float(v_oos["price"]), float(v_instock["price"]))


class TestZeroDatabaseMutationInvariant(unittest.TestCase):
    """
    CRITICAL: Verify that resolving storefront prices and preparing payloads
    NEVER mutates local storage/db/{store}/products/*.json files on disk.
    """

    def test_zero_disk_mutation_on_sample_products(self):
        sample_files = glob.glob(os.path.join(PROJECT_ROOT, "storage", "db", "jwpei", "products", "*.json"))[:5]
        self.assertTrue(len(sample_files) > 0, "No JW PEI products found to test mutation invariant")

        forex_rate = 95.0

        for fpath in sample_files:
            mtime_before = os.path.getmtime(fpath)
            with open(fpath, "r", encoding="utf-8") as f:
                content_before = f.read()
                prod_data = json.loads(content_before)

            orig_source_price = prod_data.get("source_price")

            # 1. Run pricing engine resolution
            p_inr, comp_inr = resolve_product_storefront_pricing(prod_data, forex_rate)
            self.assertGreater(p_inr, 0)

            # 2. Run full Shopify taxonomy payload preparation
            payload = prepare_product_set_payload(prod_data, forex_rate)
            self.assertIn("variants", payload)

            # 3. Verify disk file remains 100% untouched
            mtime_after = os.path.getmtime(fpath)
            with open(fpath, "r", encoding="utf-8") as f:
                content_after = f.read()

            self.assertEqual(mtime_before, mtime_after, f"File {fpath} mtime changed!")
            self.assertEqual(content_before, content_after, f"File {fpath} content mutated!")


class TestPricingEdgeCasesAndHardening(unittest.TestCase):
    """Deep verification of edge cases, string prices, store normalization, and zero-price prevention."""

    def test_low_positive_price_never_zero(self):
        """Positive price rounding must never clamp to 0.0 (prevents free product checkout bug)."""
        # A tiny fee/accessory with INR 20 rounded to nearest 100 with charm -1
        # Commercial round would be 0, minus 1 = -1 -> MUST be clamped to 99.0, NOT 0.0!
        price = apply_charm_rounding(20.0, nearest=100, charm_offset=-1)
        self.assertEqual(price, 99.0)

        price_small = apply_charm_rounding(0.50, nearest=100, charm_offset=-1)
        self.assertEqual(price_small, 99.0)

    def test_dirty_and_string_price_inputs(self):
        """Pricing engine must gracefully handle string prices, currency symbols, and dirty inputs."""
        rule = {
            "formula": "linear_markup",
            "base_usd": 89.0,
            "base_markup_inr": 2955.0,
            "per_usd_markup_inr": 14.0,
            "round_nearest": 100,
            "charm_offset": -1
        }
        # String number
        self.assertEqual(apply_pricing_formula("89.0", rule, 90.0), 10999.0)
        # None and empty
        self.assertEqual(apply_pricing_formula(None, rule, 90.0), 0.0)
        self.assertEqual(apply_pricing_formula("", rule, 90.0), 0.0)
        self.assertEqual(apply_pricing_formula("invalid", rule, 90.0), 0.0)

    def test_null_round_nearest_and_charm_offset(self):
        """Pricing engine must safely handle rules where round_nearest or charm_offset are None."""
        null_rule = {
            "formula": "standard_forex",
            "round_nearest": None,
            "charm_offset": None
        }
        # $100 at FX 90 -> 9000 -> commercial_round_half_up(9000, 100) = 9000 -> 9000 - 1 = 8999.0
        p = apply_pricing_formula(100.0, null_rule, 90.0)
        self.assertEqual(p, 8999.0)
        self.assertEqual(int(p) % 100, 99)

    def test_zero_or_negative_forex_rate_guard(self):
        """Non-positive forex rate must return 0.0 without crash or charging baseline charm."""
        rule = {"formula": "standard_forex", "round_nearest": 100, "charm_offset": -1}
        self.assertEqual(apply_pricing_formula(100.0, rule, 0.0), 0.0)
        self.assertEqual(apply_pricing_formula(100.0, rule, -90.0), 0.0)

    def test_store_slug_normalization(self):
        """Store names like 'JW PEI', 'jw-pei', 'jw_pei' must match 'jwpei' rule."""
        for variant in ["jwpei", "JW PEI", "jw-pei", "jw_pei", "JWPEI"]:
            rule = get_rule_for_product(variant)
            self.assertEqual(rule.get("formula"), "linear_markup", f"Failed for store alias '{variant}'")
            self.assertEqual(rule.get("base_usd"), 89.0)

    def test_variant_zero_or_string_price_inherits_parent(self):
        """Variant with source_price '0.00' or 0.0 must inherit parent source_price."""
        mock_prod = {
            "source_store": "jwpei",
            "title": "Fallback Bag",
            "source_price": 109.0,
            "variants": [
                {
                    "sku": "VAR-ZERO-STR",
                    "title": "Black",
                    "source_price": "0.00",
                    "in_stock": True,
                    "option_values": [{"option_name": "Color", "name": "Black"}]
                },
                {
                    "sku": "VAR-NONE",
                    "title": "Brown",
                    "source_price": None,
                    "in_stock": True,
                    "option_values": [{"option_name": "Color", "name": "Brown"}]
                }
            ]
        }
        forex_rate = 90.0
        opts, variants = resolve_options_and_variants(mock_prod, forex_rate, 109.0, None)
        self.assertEqual(len(variants), 2)
        # $109 at FX 90 -> 109 * 104 + 1709 = 13045 -> 13000 - 1 = 12999
        self.assertEqual(float(variants[0]["price"]), 12999.0)
        self.assertEqual(float(variants[1]["price"]), 12999.0)

    def test_formula_precedence_respects_custom_base_markup(self):
        """If user edits base_markup_inr in linear_markup, it must be honored."""
        custom_rule = {
            "formula": "linear_markup",
            "base_usd": 100.0,
            "base_markup_inr": 3500.0,
            "per_usd_markup_inr": 15.0,
            "fixed_offset_inr": 1709.0,  # Stale fixed offset should NOT override base_markup_inr
            "round_nearest": 100,
            "charm_offset": -1
        }
        # For $100 at FX 90:
        # raw = 100 * 90 + 3500 + 0 = 12500 -> 12500 - 1 = 12499
        # (If stale fixed_offset_inr were used, it would give 100 * 104 + 1709 = 12109 -> 12099)
        price = apply_pricing_formula(100.0, custom_rule, 90.0)
        self.assertEqual(price, 12499.0)


class TestDiscountBracketMarkupFormula(unittest.TestCase):
    """
    Verification suite for Jomashop Tissot dynamic watch pricing formula.
    Validates:
    - Markup schedule brackets & boundary precision (<25% -> 16%, 25-29.99% -> 18%, 30-39.99% -> 29%, 40-49.99% -> 40%, 50-59.99% -> 50%, 60%+ -> 70%)
    - Formula equation: Final Price = ROUND((SourceUSD × FX) × (1 + Markup), -2) - 1
    - Safety Ceiling Invariant: Final price never exceeds official brand MSRP (source_compare_at_price × FX)
    - Storefront Compare-At Strategy: Displays official brand retail price in INR (ROUND(source_compare_at_price × FX, -2) - 1)
    - Store/Vendor rule matching for Jomashop Tissot
    - Real catalog audit across all 157 Jomashop Tissot watches
    - Zero Database Mutation Invariant on disk JSON files
    """

    def setUp(self):
        self.rule = {
            "formula": "discount_bracket_markup",
            "round_nearest": 100,
            "charm_offset": -1,
            "brackets": [
                {"max_discount": 0.25, "markup": 0.16},
                {"min_discount": 0.25, "max_discount": 0.30, "markup": 0.18},
                {"min_discount": 0.30, "max_discount": 0.40, "markup": 0.29},
                {"min_discount": 0.40, "max_discount": 0.50, "markup": 0.40},
                {"min_discount": 0.50, "max_discount": 0.60, "markup": 0.50},
                {"min_discount": 0.60, "markup": 0.70}
            ]
        }
        self.forex_rate = 90.0

    def test_bracket_markup_schedule_tiers(self):
        # Tier 1: < 25% -> 16%
        self.assertEqual(resolve_bracket_markup(0.00), 0.16)
        self.assertEqual(resolve_bracket_markup(0.10), 0.16)
        self.assertEqual(resolve_bracket_markup(0.20), 0.16)
        self.assertEqual(resolve_bracket_markup(0.2499), 0.16)

        # Tier 2: 25% - 29.99% -> 18%
        self.assertEqual(resolve_bracket_markup(0.25), 0.18)
        self.assertEqual(resolve_bracket_markup(0.27), 0.18)
        self.assertEqual(resolve_bracket_markup(0.2999), 0.18)

        # Tier 3: 30% - 39.99% -> 29%
        self.assertEqual(resolve_bracket_markup(0.30), 0.29)
        self.assertEqual(resolve_bracket_markup(0.35), 0.29)
        self.assertEqual(resolve_bracket_markup(0.3999), 0.29)

        # Tier 4: 40% - 49.99% -> 40%
        self.assertEqual(resolve_bracket_markup(0.40), 0.40)
        self.assertEqual(resolve_bracket_markup(0.45), 0.40)
        self.assertEqual(resolve_bracket_markup(0.4999), 0.40)

        # Tier 5: 50% - 59.99% -> 50%
        self.assertEqual(resolve_bracket_markup(0.50), 0.50)
        self.assertEqual(resolve_bracket_markup(0.55), 0.50)
        self.assertEqual(resolve_bracket_markup(0.5999), 0.50)

        # Tier 6: 60%+ -> 70%
        self.assertEqual(resolve_bracket_markup(0.60), 0.70)
        self.assertEqual(resolve_bracket_markup(0.694), 0.70)
        self.assertEqual(resolve_bracket_markup(0.85), 0.70)

    def test_formula_equation_and_charm(self):
        # Discount: (1000 - 500) / 1000 = 50% -> bracket 50% -> markup 0.50
        # SourceUSD: 500, FX: 90.0
        # Raw = (500 * 90) * 1.50 = 45000 * 1.50 = 67500
        # ROUND(67500, -2) - 1 = 67500 - 1 = 67499
        p = apply_pricing_formula(500.0, self.rule, 90.0, compare_source_price=1000.0)
        self.assertEqual(p, 67499.0)
        self.assertEqual(int(p) % 100, 99)

    def test_safety_ceiling_wnba_watch(self):
        # Tissot WNBA Watch: Source USD $450, Compare At MSRP $515
        # Discount = (515 - 450) / 515 = 12.62% -> Markup 16% (0.16)
        # Uncapped at FX 90.0: (450 * 90) * 1.16 = 40500 * 1.16 = 46980 -> 47000 - 1 = 46999
        # MSRP at FX 90.0: 515 * 90 = 46350 -> ROUND(46350, -2) - 1 = 46400 - 1 = 46399
        # Invariant: Final Price must NEVER exceed MSRP! Capped at 46399.
        p_inr = apply_pricing_formula(450.0, self.rule, 90.0, compare_source_price=515.0)
        self.assertEqual(p_inr, 46399.0)
        self.assertLessEqual(p_inr, 46399.0)

        # Storefront resolution should suppress compare_at_price since selling price equals MSRP
        p, comp = resolve_storefront_pricing(450.0, 515.0, "jomashop", "Watches", 90.0, vendor="Tissot")
        self.assertEqual(p, 46399.0)
        self.assertIsNone(comp)

    def test_safety_ceiling_live_forex(self):
        # Test with live FX ~95.90693
        fx = 95.90693
        # WNBA uncapped: (450 * fx) * 1.16 = 50063.42 -> 50099
        # MSRP: 515 * fx = 49392.07 -> 49400 - 1 = 49399
        p_inr = apply_pricing_formula(450.0, self.rule, fx, compare_source_price=515.0)
        self.assertEqual(p_inr, 49399.0)
        self.assertLessEqual(p_inr, 49399.0)

    def test_safety_ceiling_extreme_low_discount(self):
        # Watch with 1% discount: USD $495, MSRP $500, FX 100.0
        # Discount = 1% -> Markup 16%
        # Uncapped: 495 * 100 * 1.16 = 57420 -> 57400 - 1 = 57399
        # MSRP: 500 * 100 = 50000 -> 50000 - 1 = 49999
        p_inr = apply_pricing_formula(495.0, self.rule, 100.0, compare_source_price=500.0)
        self.assertEqual(p_inr, 49999.0)

    def test_compare_at_strategy_high_discount(self):
        # High discount: USD $329, MSRP $1075, FX 90.0
        # Discount = (1075 - 329) / 1075 = 69.4% -> 70% markup
        # Selling price: (329 * 90) * 1.70 = 29610 * 1.70 = 50337 -> 50300 - 1 = 50299
        # MSRP: 1075 * 90 = 96750 -> 96800 - 1 = 96799
        p, comp = resolve_storefront_pricing(329.0, 1075.0, "jomashop", "Watches", 90.0, vendor="Tissot")
        self.assertEqual(p, 50299.0)
        self.assertEqual(comp, 96799.0)
        self.assertGreater(comp, p)
        # Verify genuine luxury savings off brand retail
        self.assertEqual(int(comp) % 100, 99)
        self.assertEqual(int(p) % 100, 99)

    def test_vendor_rule_resolution(self):
        # All watch brands on Jomashop resolve to discount_bracket_markup (ADR 0028)
        brands = ["Tissot", "Citizen", "Movado", "Seiko", "Michael Kors", "Versace", "Ferragamo"]
        for brand in brands:
            rule = get_rule_for_product("jomashop", "Watches", vendor=brand)
            self.assertEqual(rule.get("formula"), "discount_bracket_markup", f"Brand {brand} did not resolve discount_bracket_markup")

        # Case-insensitivity across brands
        self.assertEqual(get_rule_for_product("jomashop", "Watches", vendor="tissot").get("formula"), "discount_bracket_markup")
        self.assertEqual(get_rule_for_product("jomashop", "Watches", vendor="TISSOT").get("formula"), "discount_bracket_markup")
        self.assertEqual(get_rule_for_product("jomashop", "Watches", vendor="MOVADO").get("formula"), "discount_bracket_markup")
        self.assertEqual(get_rule_for_product("jomashop", "Watches", vendor="seiko").get("formula"), "discount_bracket_markup")

        # Universal Watches and Watch category across any store (including stores with default bag markups)
        self.assertEqual(get_rule_for_product("michaelkors", "Watches").get("formula"), "discount_bracket_markup")
        self.assertEqual(get_rule_for_product("michaelkors", "Watch").get("formula"), "discount_bracket_markup")
        self.assertEqual(get_rule_for_product("jwpei", "Watches").get("formula"), "discount_bracket_markup")
        self.assertEqual(get_rule_for_product("jwpei", "Watch").get("formula"), "discount_bracket_markup")
        self.assertEqual(get_rule_for_product("nordstrom", "Watches").get("formula"), "discount_bracket_markup")
        self.assertEqual(get_rule_for_product("unknown_store", "Watches").get("formula"), "discount_bracket_markup")
        self.assertEqual(get_rule_for_product("unknown_store", "Watch").get("formula"), "discount_bracket_markup")

        # Non-watch items in configured stores preserve their store-specific markups
        self.assertEqual(get_rule_for_product("michaelkors", "Handbags").get("formula"), "price_bracket_markup")
        self.assertEqual(get_rule_for_product("jwpei", "Shoulder Bags").get("formula"), "linear_markup")

        # Configured stores preserve their store-specific markups
        self.assertEqual(get_rule_for_product("coach", "Handbags").get("formula"), "price_bracket_markup")
        self.assertEqual(get_rule_for_product("coach", "Shoulder Bags", vendor="COACH").get("formula"), "price_bracket_markup")

        # Unconfigured non-watch store falls back to standard_forex
        rule_unconf = get_rule_for_product("footlocker", "Shoulder Bags", vendor="Nike")
        self.assertEqual(rule_unconf.get("formula"), "standard_forex")

    def test_real_jomashop_tissot_catalog_pricing(self):
        # Load real Tissot products from disk
        pattern = os.path.join(PROJECT_ROOT, "storage", "db", "jomashop", "products", "*.json")
        files = glob.glob(pattern)
        tissot_count = 0
        forex_rate = 95.0

        for fpath in files:
            with open(fpath, "r", encoding="utf-8") as f:
                prod = json.load(f)
            title = prod.get("title", "")
            vendor = prod.get("vendor", "")
            if "tissot" not in title.lower() and "tissot" not in vendor.lower():
                continue

            tissot_count += 1
            p_inr, comp_inr = resolve_product_storefront_pricing(prod, forex_rate)
            self.assertGreater(p_inr, 0.0)
            self.assertEqual(int(p_inr) % 100, 99, f"Product {prod.get('id')} price {p_inr} not charm ending in 99")

            src_comp = float(prod.get("source_compare_at_price") or 0.0)
            if src_comp > 0:
                msrp_inr = commercial_round_half_up(src_comp * forex_rate, 100) - 1
                self.assertLessEqual(p_inr, msrp_inr, f"Product {prod.get('id')} price {p_inr} exceeded MSRP {msrp_inr}")

            if comp_inr is not None:
                self.assertGreater(comp_inr, p_inr)
                self.assertEqual(int(comp_inr) % 100, 99)

        self.assertEqual(tissot_count, 157, f"Expected 157 Tissot watches, found {tissot_count}")

    def test_all_574_jomashop_watches_pricing(self):
        """Audit all 574 Jomashop watches across all 7 brands applying discount_bracket_markup."""
        pattern = os.path.join(PROJECT_ROOT, "storage", "db", "jomashop", "products", "*.json")
        files = glob.glob(pattern)
        self.assertEqual(len(files), 574, f"Expected exactly 574 Jomashop watch files, found {len(files)}")
        forex_rate = 95.0

        brand_counts = {}
        for fpath in files:
            with open(fpath, "r", encoding="utf-8") as f:
                prod = json.load(f)

            vendor = prod.get("vendor") or prod.get("brand") or "Unknown"
            brand_counts[vendor] = brand_counts.get(vendor, 0) + 1

            p_inr, comp_inr = resolve_product_storefront_pricing(prod, forex_rate)
            self.assertGreater(p_inr, 0.0, f"Product {prod.get('id')} ({vendor}) generated invalid price {p_inr}")
            self.assertEqual(int(p_inr) % 100, 99, f"Product {prod.get('id')} price {p_inr} not charm ending in 99")

            # Verify brand MSRP safety ceiling
            src_comp = float(prod.get("source_compare_at_price") or 0.0)
            src_price = float(prod.get("source_price") or 0.0)
            if src_comp > src_price:
                msrp_inr = commercial_round_half_up(src_comp * forex_rate, 100) - 1
                self.assertLessEqual(p_inr, msrp_inr, f"Product {prod.get('id')} ({vendor}) price {p_inr} exceeded MSRP {msrp_inr}")

            if comp_inr is not None:
                self.assertGreater(comp_inr, p_inr)
                self.assertEqual(int(comp_inr) % 100, 99)

        expected_brands = {"Tissot", "Citizen", "Movado", "Seiko", "Michael Kors", "Versace", "Ferragamo"}
        self.assertTrue(expected_brands.issubset(set(brand_counts.keys())), f"Missing expected brands: {expected_brands - set(brand_counts.keys())}")
        self.assertEqual(sum(brand_counts.values()), 574)

    def test_multivariant_watch_color_pricing_independence(self):
        """Verify watches with multiple color/finish variants preserve individual pricing."""
        mock_watch = {
            "source_store": "jomashop",
            "vendor": "Citizen",
            "product_type": "Watches",
            "title": "Citizen Eco-Drive Promaster Diver",
            "source_price": 250.0,
            "source_compare_at_price": 500.0,
            "specifications": {"Case Diameter": "44 mm"},
            "variants": [
                {
                    "sku": "CIT-BLUE-44",
                    "title": "Blue Dial / Steel",
                    "color": "Blue",
                    "source_price": 250.0,
                    "source_compare_at_price": 500.0,
                    "in_stock": True,
                    "image_url": "https://cdn2.jomashop.com/blue.jpg"
                },
                {
                    "sku": "CIT-GOLD-44",
                    "title": "Gold Tone / Black Dial",
                    "color": "Gold",
                    "source_price": 350.0,
                    "source_compare_at_price": 600.0,
                    "in_stock": True,
                    "image_url": "https://cdn2.jomashop.com/gold.jpg"
                },
                {
                    "sku": "CIT-STEALTH-44",
                    "title": "All Black PVD",
                    "color": "Black",
                    "source_price": 420.0,
                    "source_compare_at_price": 500.0,
                    "in_stock": True,
                    "image_url": "https://cdn2.jomashop.com/black.jpg"
                }
            ]
        }
        forex_rate = 95.0
        opts, var_inputs = resolve_options_and_variants(mock_watch, forex_rate, 250.0, 500.0)

        # Must preserve all 3 variants without dropping or deduplicating
        self.assertEqual(len(var_inputs), 3, f"Expected 3 variants, got {len(var_inputs)}")
        opt_names = [o["name"] for o in opts]
        self.assertIn("Color", opt_names)

        # Variant 1: $250 vs $500 -> 50% discount -> 50% markup: 250 * 95 * 1.50 = 35625 -> 35599
        v_blue = next(v for v in var_inputs if "CIT-BLUE-44" in v["sku"])
        self.assertEqual(float(v_blue["price"]), 35599.0)
        self.assertEqual(float(v_blue["compareAtPrice"]), 47499.0)

        # Variant 2: $350 vs $600 -> 41.67% discount -> 40% markup: 350 * 95 * 1.40 = 46550 -> 46599
        v_gold = next(v for v in var_inputs if "CIT-GOLD-44" in v["sku"])
        self.assertEqual(float(v_gold["price"]), 46599.0)
        self.assertEqual(float(v_gold["compareAtPrice"]), 56999.0)

        # Variant 3: $420 vs $500 -> 16.0% discount -> 16% markup: 420 * 95 * 1.16 = 46284 -> 46299
        # (capped at MSRP: $500 * 95 = 47500 -> 47499, 46299 <= 47499)
        v_black = next(v for v in var_inputs if "CIT-STEALTH-44" in v["sku"])
        self.assertEqual(float(v_black["price"]), 46299.0)
        self.assertEqual(float(v_black["compareAtPrice"]), 47499.0)

        # All variants end in .99
        for v in var_inputs:
            self.assertEqual(int(float(v["price"])) % 100, 99)

    def test_multivariant_watch_dial_color_no_duplicate_color_dimension(self):
        """Verify that when variants define Dial Color option, no duplicate Color dimension is appended."""
        prod_dial = {
            "product_type": "Watches",
            "source_store": "jomashop",
            "vendor": "Citizen",
            "source_price": 200.0,
            "source_compare_at_price": 400.0,
            "specifications": {"Case Diameter": "42 mm"},
            "variants": [
                {
                    "sku": "CIT-DIAL-BLUE",
                    "title": "Blue",
                    "option_values": [{"option_name": "Dial Color", "name": "Blue"}],
                    "source_price": 200.0,
                    "source_compare_at_price": 400.0,
                    "in_stock": True
                },
                {
                    "sku": "CIT-DIAL-BLACK",
                    "title": "Black",
                    "option_values": [{"option_name": "Dial Color", "name": "Black"}],
                    "source_price": 220.0,
                    "source_compare_at_price": 400.0,
                    "in_stock": True
                }
            ]
        }
        opts, var_inputs = resolve_options_and_variants(prod_dial, 95.0, 200.0, 400.0)
        opt_names = [o["name"] for o in opts]
        self.assertIn("Dial Color", opt_names)
        self.assertNotIn("Color", opt_names)
        self.assertEqual(len(var_inputs), 2)
        for v in var_inputs:
            ov_names = [ov["optionName"] for ov in v["optionValues"]]
            self.assertEqual(len(ov_names), len(set(ov_names)), f"Duplicate option names found: {ov_names}")

    def test_multivariant_watch_independent_variant_compare_at(self):
        """Verify that variants with separate source_compare_at_price compute independent discount tiers."""
        mock_watch = {
            "product_type": "Watches",
            "source_store": "jomashop",
            "vendor": "Movado",
            "source_price": 300.0,
            "source_compare_at_price": 600.0,
            "variants": [
                {
                    "sku": "MOV-STANDARD",
                    "title": "Standard Dial",
                    "color": "Silver",
                    "source_price": 300.0,
                    "source_compare_at_price": 600.0,
                    "in_stock": True
                },
                {
                    "sku": "MOV-DIAMOND",
                    "title": "Diamond Marker Dial",
                    "color": "Diamond Silver",
                    "source_price": 400.0,
                    "source_compare_at_price": 1000.0,
                    "in_stock": True
                }
            ]
        }
        forex_rate = 95.0
        opts, var_inputs = resolve_options_and_variants(mock_watch, forex_rate, 300.0, 600.0)
        v_std = next(v for v in var_inputs if "MOV-STANDARD" in v["sku"])
        v_dia = next(v for v in var_inputs if "MOV-DIAMOND" in v["sku"])

        # v_std: 300 * 95 * 1.50 = 42750 -> 42799. compare: 600 * 95 = 57000 -> 56999
        self.assertEqual(float(v_std["price"]), 42799.0)
        self.assertEqual(float(v_std["compareAtPrice"]), 56999.0)

        # v_dia: 400 * 95 * 1.70 = 64600 -> 64599. compare: 1000 * 95 = 95000 -> 94999
        self.assertEqual(float(v_dia["price"]), 64599.0)
        self.assertEqual(float(v_dia["compareAtPrice"]), 94999.0)

    def test_inverted_compare_at_never_caps_below_cost(self):
        # Defensively protect against bad scraper data where compare_at < source_price
        # Supplier cost: $500, Bad compare_at: $400, FX: 90.0
        # Invariant: Must NOT cap below cost! Discount is 0% -> applies 16% markup -> 52199.0
        p_inr = apply_pricing_formula(500.0, self.rule, 90.0, compare_source_price=400.0)
        self.assertEqual(p_inr, 52199.0)
        self.assertGreater(p_inr, 500.0 * 90.0)

        # In resolve_storefront_pricing, compare_at must be cleanly suppressed
        p, comp = resolve_storefront_pricing(500.0, 400.0, "jomashop", "Watches", 90.0, vendor="Tissot")
        self.assertEqual(p, 52199.0)
        self.assertIsNone(comp)

    def test_equal_compare_at_preserves_minimum_markup(self):
        # Watch with 0% discount (MSRP == Source price): $500 and $500
        # Invariant: Must apply 16% markup without capping down to cost
        p_inr = apply_pricing_formula(500.0, self.rule, 90.0, compare_source_price=500.0)
        self.assertEqual(p_inr, 52199.0)
        self.assertGreater(p_inr, 500.0 * 90.0)

        p, comp = resolve_storefront_pricing(500.0, 500.0, "jomashop", "Watches", 90.0, vendor="Tissot")
        self.assertEqual(p, 52199.0)
        self.assertIsNone(comp)

    def test_bare_rule_defaults_to_hundred_and_charm_minus_one(self):
        # If caller provides bare {"formula": "discount_bracket_markup"} without round_nearest or charm_offset,
        # it must default to round_nearest=100 and charm_offset=-1
        bare_rule = {"formula": "discount_bracket_markup"}
        p = apply_pricing_formula(500.0, bare_rule, 90.0, compare_source_price=1000.0)
        self.assertEqual(p, 67499.0)
        self.assertEqual(int(p) % 100, 99)

    def test_dirty_and_currency_string_compare_at(self):
        # Gracefully handle string compare_at with currency symbols and commas
        p = apply_pricing_formula(500.0, self.rule, 90.0, compare_source_price="$1,000.00")
        self.assertEqual(p, 67499.0)

        p_str, comp_str = resolve_storefront_pricing(500.0, "$1,000.00", "jomashop", "Watches", 90.0, vendor="Tissot")
        self.assertEqual(p_str, 67499.0)
        self.assertEqual(comp_str, 89999.0)

    def test_variant_oos_floor_with_discount_bracket_markup(self):
        # Multi-variant product with discount_bracket_markup
        # In-stock variant has 50% discount -> 50% markup -> ₹67,499
        # OOS variant has low price and low discount -> ₹37,799
        # OOS Price Floor Invariant: OOS variant must be clamped to ₹67,499!
        mock_prod = {
            "source_store": "jomashop",
            "vendor": "Tissot",
            "product_type": "Watches",
            "source_price": 500.0,
            "source_compare_at_price": 1000.0,
            "variants": [
                {
                    "sku": "TISSOT-IN-STOCK",
                    "title": "Steel",
                    "source_price": 500.0,
                    "source_compare_at_price": 1000.0,
                    "in_stock": True,
                    "option_values": [{"option_name": "Color", "name": "Steel"}]
                },
                {
                    "sku": "TISSOT-OOS-CHEAP",
                    "title": "Leather",
                    "source_price": 400.0,
                    "source_compare_at_price": 420.0,
                    "in_stock": False,
                    "option_values": [{"option_name": "Color", "name": "Leather"}]
                }
            ]
        }
        opts, variants = resolve_options_and_variants(mock_prod, 90.0, 500.0, 1000.0)
        v_in = next(v for v in variants if "TISSOT-IN-STOCK" in v["sku"])
        v_oos = next(v for v in variants if "TISSOT-OOS-CHEAP" in v["sku"])

        self.assertEqual(float(v_in["price"]), 67499.0)
        self.assertEqual(float(v_oos["price"]), 67499.0)

    def test_zero_disk_mutation_on_jomashop_tissot(self):
        # Verify Zero Database Mutation Invariant on Jomashop Tissot products
        pattern = os.path.join(PROJECT_ROOT, "storage", "db", "jomashop", "products", "*.json")
        sample_files = []
        for f in glob.glob(pattern):
            with open(f, "r", encoding="utf-8") as fp:
                if "tissot" in fp.read().lower():
                    sample_files.append(f)
            if len(sample_files) >= 5:
                break
        self.assertTrue(len(sample_files) > 0)

        forex_rate = 95.0
        for fpath in sample_files:
            mtime_before = os.path.getmtime(fpath)
            with open(fpath, "r", encoding="utf-8") as f:
                content_before = f.read()
                prod_data = json.loads(content_before)

            p_inr, comp_inr = resolve_product_storefront_pricing(prod_data, forex_rate)
            payload = prepare_product_set_payload(prod_data, forex_rate)

            mtime_after = os.path.getmtime(fpath)
            with open(fpath, "r", encoding="utf-8") as f:
                content_after = f.read()

            self.assertEqual(mtime_before, mtime_after)
            self.assertEqual(content_before, content_after)


class TestMichaelKorsTieredPricing(unittest.TestCase):
    """
    Verify Michael Kors Outlet tiered pricing formula (ADR 0028):
    - Base cost <= 10K INR: +45% markup
    - Base cost 10K - 15K INR: +40% markup
    - Base cost > 15K INR: +35% markup
    - Commercial round-half-up to nearest 100 with charm -1 (ends in .99)
    """

    def setUp(self):
        self.forex_rate = 95.0
        self.rule = {
            "formula": "price_bracket_markup",
            "round_nearest": 100,
            "charm_offset": -1,
            "brackets": [
                {"max_inr": 10000, "markup_percent": 0.45},
                {"min_inr": 10000, "max_inr": 15000, "markup_percent": 0.40},
                {"min_inr": 15000, "markup_percent": 0.35}
            ]
        }

    def test_bracket_markup_resolution(self):
        brackets = self.rule["brackets"]
        # <= 10K
        self.assertEqual(resolve_price_bracket_markup(5000.0, brackets), 0.45)
        self.assertEqual(resolve_price_bracket_markup(10000.0, brackets), 0.45)
        # 10K - 15K
        self.assertEqual(resolve_price_bracket_markup(10000.01, brackets), 0.40)
        self.assertEqual(resolve_price_bracket_markup(12500.0, brackets), 0.40)
        self.assertEqual(resolve_price_bracket_markup(15000.0, brackets), 0.40)
        # > 15K
        self.assertEqual(resolve_price_bracket_markup(15000.01, brackets), 0.35)
        self.assertEqual(resolve_price_bracket_markup(25000.0, brackets), 0.35)

    def test_tier_price_calculations(self):
        # Tier 1: $49.99 * 95.0 = 4749.05 -> +45% = 6886.12 -> 6899.0
        p1 = apply_pricing_formula(49.99, self.rule, self.forex_rate)
        self.assertEqual(p1, 6899.0)
        self.assertEqual(int(p1) % 100, 99)

        # Tier 2: $129.50 * 95.0 = 12302.50 -> +40% = 17223.50 -> 17199.0
        p2 = apply_pricing_formula(129.50, self.rule, self.forex_rate)
        self.assertEqual(p2, 17199.0)
        self.assertEqual(int(p2) % 100, 99)

        # Tier 3: $199.50 * 95.0 = 18952.50 -> +35% = 25585.88 -> 25599.0
        p3 = apply_pricing_formula(199.50, self.rule, self.forex_rate)
        self.assertEqual(p3, 25599.0)
        self.assertEqual(int(p3) % 100, 99)

    def test_rule_resolution_for_michaelkors_store(self):
        resolved_rule = get_rule_for_product("michaelkors")
        self.assertEqual(resolved_rule.get("formula"), "price_bracket_markup")
        self.assertEqual(len(resolved_rule.get("brackets", [])), 3)

    def test_compare_at_resolution_michaelkors(self):
        # sp = $119.0 (base 11305 -> Tier 2: +40% -> 15827 -> 15799)
        # comp = $199.5 (base 18952.5 -> Tier 3: +35% -> 25585.88 -> 25599)
        price, compare_at = resolve_storefront_pricing(
            119.0, 199.5, "michaelkors", "Crossbody Bags", self.forex_rate
        )
        self.assertEqual(price, 15799.0)
        self.assertEqual(compare_at, 25599.0)
        self.assertTrue(compare_at > price)
        self.assertEqual(int(price) % 100, 99)
        self.assertEqual(int(compare_at) % 100, 99)

    def test_zero_disk_mutation_on_michaelkors(self):
        pattern = os.path.join(PROJECT_ROOT, "storage", "db", "michaelkors", "products", "*.json")
        sample_files = glob.glob(pattern)[:5]
        self.assertTrue(len(sample_files) > 0)

        forex_rate = 95.0
        for fpath in sample_files:
            mtime_before = os.path.getmtime(fpath)
            with open(fpath, "r", encoding="utf-8") as f:
                content_before = f.read()
                prod_data = json.loads(content_before)

            p_inr, comp_inr = resolve_product_storefront_pricing(prod_data, forex_rate)
            payload = prepare_product_set_payload(prod_data, forex_rate)

            mtime_after = os.path.getmtime(fpath)
            with open(fpath, "r", encoding="utf-8") as f:
                content_after = f.read()

            self.assertEqual(mtime_before, mtime_after)
            self.assertEqual(content_before, content_after)


class TestCoachTieredPricing(unittest.TestCase):
    """
    Verify Coach tiered pricing formula (ADR 0028):
    - Base cost <= 10K INR: +45% markup
    - Base cost 10K - 15K INR: +40% markup
    - Base cost > 15K INR: +35% markup
    - Commercial round-half-up to nearest 100 with charm -1 (ends in .99)
    - Full variant pricing differentiation (e.g. $99 vs $119 variants)
    - Zero Database Mutation Invariant across Coach catalog
    """

    def setUp(self):
        self.forex_rate = 95.0
        self.rule = {
            "formula": "price_bracket_markup",
            "round_nearest": 100,
            "charm_offset": -1,
            "brackets": [
                {"max_inr": 10000, "markup_percent": 0.45},
                {"min_inr": 10000, "max_inr": 15000, "markup_percent": 0.40},
                {"min_inr": 15000, "markup_percent": 0.35}
            ]
        }

    def test_bracket_markup_resolution(self):
        brackets = self.rule["brackets"]
        # <= 10K: +45%
        self.assertEqual(resolve_price_bracket_markup(5000.0, brackets), 0.45)
        self.assertEqual(resolve_price_bracket_markup(10000.0, brackets), 0.45)
        # 10K - 15K: +40%
        self.assertEqual(resolve_price_bracket_markup(10000.01, brackets), 0.40)
        self.assertEqual(resolve_price_bracket_markup(12500.0, brackets), 0.40)
        self.assertEqual(resolve_price_bracket_markup(15000.0, brackets), 0.40)
        # > 15K: +35%
        self.assertEqual(resolve_price_bracket_markup(15000.01, brackets), 0.35)
        self.assertEqual(resolve_price_bracket_markup(25000.0, brackets), 0.35)

    def test_tier_price_calculations(self):
        # Tier 1: $99.0 * 95.0 = 9405.0 -> +45% = 13637.25 -> round 13600 - 1 = 13599.0
        p1 = apply_pricing_formula(99.0, self.rule, self.forex_rate)
        self.assertEqual(p1, 13599.0)
        self.assertEqual(int(p1) % 100, 99)

        # Tier 2: $119.0 * 95.0 = 11305.0 -> +40% = 15827.0 -> round 15800 - 1 = 15799.0
        p2 = apply_pricing_formula(119.0, self.rule, self.forex_rate)
        self.assertEqual(p2, 15799.0)
        self.assertEqual(int(p2) % 100, 99)

        # Tier 3: $195.0 * 95.0 = 18525.0 -> +35% = 25008.75 -> round 25000 - 1 = 24999.0
        p3 = apply_pricing_formula(195.0, self.rule, self.forex_rate)
        self.assertEqual(p3, 24999.0)
        self.assertEqual(int(p3) % 100, 99)

    def test_rule_resolution_for_coach_store(self):
        resolved_rule = get_rule_for_product("coach")
        self.assertEqual(resolved_rule.get("formula"), "price_bracket_markup")
        self.assertEqual(len(resolved_rule.get("brackets", [])), 3)

        # Case-insensitivity and aliases
        self.assertEqual(get_rule_for_product("COACH").get("formula"), "price_bracket_markup")
        self.assertEqual(get_rule_for_product("Coach").get("formula"), "price_bracket_markup")
        self.assertEqual(get_rule_for_product("coach", "Handbags").get("formula"), "price_bracket_markup")
        self.assertEqual(get_rule_for_product("coach", "Shoes & Footwear").get("formula"), "price_bracket_markup")
        self.assertEqual(get_rule_for_product("coach", "Wallets & Small Goods").get("formula"), "price_bracket_markup")

    def test_multi_price_variant_calculations_99_vs_119(self):
        """
        Verify product with $99 vs $119 variants (like Coach Pouch In Signature Canvas)
        resolves independent pricing across tiers:
        - $99 variant (Tier 1 <= 10K): ₹13,599.0
        - $119 variant (Tier 2 10K-15K): ₹15,799.0
        """
        mock_pouch = {
            "source_store": "coach",
            "vendor": "COACH",
            "title": "Pouch In Signature Canvas",
            "source_price": 99.0,
            "product_type": "Handbags",
            "variants": [
                {
                    "sku": "CEU08 SV/BK",
                    "title": "Silver/Black",
                    "source_price": 99.0,
                    "in_stock": True,
                    "option_values": [{"option_name": "Color", "name": "Silver/Black"}]
                },
                {
                    "sku": "CFR91 SVXAM",
                    "title": "Sv/Walnut/Black",
                    "source_price": 119.0,
                    "in_stock": True,
                    "option_values": [{"option_name": "Color", "name": "Sv/Walnut/Black"}]
                }
            ]
        }
        opts, variants = resolve_options_and_variants(mock_pouch, self.forex_rate, 99.0, None)
        self.assertEqual(len(variants), 2)
        v_99 = next(v for v in variants if "CEU08 SV/BK" in v["sku"])
        v_119 = next(v for v in variants if "CFR91 SVXAM" in v["sku"])

        self.assertEqual(float(v_99["price"]), 13599.0)
        self.assertEqual(float(v_119["price"]), 15799.0)
        self.assertEqual(int(float(v_99["price"])) % 100, 99)
        self.assertEqual(int(float(v_119["price"])) % 100, 99)

    def test_real_coach_catalog_pouch_variant_pricing(self):
        """Verify real Coach Pouch product file with $99 and $119 variants."""
        fpath = os.path.join(PROJECT_ROOT, "storage", "db", "coach", "products", "0027f9241db46df8.json")
        self.assertTrue(os.path.exists(fpath), f"File {fpath} does not exist")
        with open(fpath, "r", encoding="utf-8") as f:
            prod_data = json.load(f)

        opts, variants = resolve_options_and_variants(prod_data, self.forex_rate, 99.0, None)
        self.assertEqual(len(variants), 9)

        # Check prices of $99 and $119 variants
        for v in variants:
            price = float(v["price"])
            self.assertEqual(int(price) % 100, 99)
            # Variants with source_price 119: 15799.0
            # Variants with source_price 99: 13599.0
            self.assertIn(price, [13599.0, 15799.0])

    def test_all_573_coach_products_pricing_audit(self):
        """Audit all 573 Coach products applying price_bracket_markup."""
        pattern = os.path.join(PROJECT_ROOT, "storage", "db", "coach", "products", "*.json")
        files = glob.glob(pattern)
        self.assertEqual(len(files), 573, f"Expected 573 Coach products, found {len(files)}")
        forex_rate = 95.0

        for fpath in files:
            with open(fpath, "r", encoding="utf-8") as f:
                prod = json.load(f)

            p_inr, comp_inr = resolve_product_storefront_pricing(prod, forex_rate)
            self.assertGreater(p_inr, 0.0, f"Product {prod.get('id')} produced zero/negative price {p_inr}")
            self.assertEqual(int(p_inr) % 100, 99, f"Product {prod.get('id')} price {p_inr} not charm ending in 99")

            if comp_inr is not None:
                self.assertGreater(comp_inr, p_inr)
                self.assertEqual(int(comp_inr) % 100, 99)

    def test_zero_disk_mutation_on_coach(self):
        pattern = os.path.join(PROJECT_ROOT, "storage", "db", "coach", "products", "*.json")
        sample_files = glob.glob(pattern)[:5]
        self.assertTrue(len(sample_files) > 0)

        forex_rate = 95.0
        for fpath in sample_files:
            mtime_before = os.path.getmtime(fpath)
            with open(fpath, "r", encoding="utf-8") as f:
                content_before = f.read()
                prod_data = json.loads(content_before)

            p_inr, comp_inr = resolve_product_storefront_pricing(prod_data, forex_rate)
            payload = prepare_product_set_payload(prod_data, forex_rate)

            mtime_after = os.path.getmtime(fpath)
            with open(fpath, "r", encoding="utf-8") as f:
                content_after = f.read()

            self.assertEqual(mtime_before, mtime_after)
            self.assertEqual(content_before, content_after)

    def test_coach_boundary_edge_cases(self):
        """Verify strict bracket boundary transitions, zero and negative inputs for Coach."""
        # Exactly 10,000 INR base cost: 10000 / 95 = 105.263158 USD -> Tier 1 (+45%) -> 14,500 -> 14,499.0
        p_boundary_10k = apply_pricing_formula(10000.0 / 95.0, self.rule, 95.0)
        self.assertEqual(p_boundary_10k, 14499.0)

        # Just over 10,000 INR base cost: 10001 / 95 = 105.273684 USD -> Tier 2 (+40%) -> 14,001.4 -> 13,999.0
        p_over_10k = apply_pricing_formula(10001.0 / 95.0, self.rule, 95.0)
        self.assertEqual(p_over_10k, 13999.0)

        # Exactly 15,000 INR base cost: 15000 / 95 = 157.894737 USD -> Tier 2 (+40%) -> 21,000 -> 20,999.0
        p_boundary_15k = apply_pricing_formula(15000.0 / 95.0, self.rule, 95.0)
        self.assertEqual(p_boundary_15k, 20999.0)

        # Just over 15,000 INR base cost: 15001 / 95 = 157.905263 USD -> Tier 3 (+35%) -> 20,251.35 -> 20,299.0
        p_over_15k = apply_pricing_formula(15001.0 / 95.0, self.rule, 95.0)
        self.assertEqual(p_over_15k, 20299.0)

        # Zero and negative inputs
        self.assertEqual(apply_pricing_formula(0.0, self.rule, 95.0), 0.0)
        self.assertEqual(apply_pricing_formula(-50.0, self.rule, 95.0), 0.0)

    def test_coach_compare_at_price_resolution(self):
        """Verify compare-at handling for Coach when compare_at is present vs equal/inverted."""
        # Valid discount: USD $99 vs Compare $150
        p, comp = resolve_storefront_pricing(99.0, 150.0, "coach", "Handbags", 95.0)
        self.assertEqual(p, 13599.0)
        self.assertEqual(comp, 19999.0)
        self.assertGreater(comp, p)
        self.assertEqual(int(comp) % 100, 99)

        # Equal compare-at suppressed
        p_eq, comp_eq = resolve_storefront_pricing(99.0, 99.0, "coach", "Handbags", 95.0)
        self.assertEqual(p_eq, 13599.0)
        self.assertIsNone(comp_eq)

        # Inverted compare-at suppressed
        p_inv, comp_inv = resolve_storefront_pricing(99.0, 89.0, "coach", "Handbags", 95.0)
        self.assertEqual(p_inv, 13599.0)
        self.assertIsNone(comp_inv)



class TestFreshnerWatchPriceFluctuationCompatibility(unittest.TestCase):
    """
    Verify freshner daemon compatibility with discount_bracket_markup across price fluctuations.
    Invariants:
    1. Fluctuating supplier USD price automatically recalculates storefront INR price based on updated discount tier.
    2. Zero mutation of local USD database price fields (clean-room invariant).
    3. Independent variant-level price shift calculations.
    4. Delta event structure captures calculated new_storefront_price_inr.
    """

    def setUp(self):
        self.forex_rate = 95.0

    def test_supplier_price_fluctuation_dynamic_recalculation(self):
        # Watch initially $300, MSRP $600 -> 50% discount -> 50% markup: 300 * 95 * 1.50 = 42750 -> 42799
        p_orig, comp_orig = resolve_storefront_pricing(300.0, 600.0, "jomashop", "Watches", self.forex_rate, vendor="Seiko")
        self.assertEqual(p_orig, 42799.0)
        self.assertEqual(comp_orig, 56999.0)

        # Supplier price drops to $240, MSRP remains $600 -> 60% discount -> 70% markup: 240 * 95 * 1.70 = 38760 -> 38799
        p_drop, comp_drop = resolve_storefront_pricing(240.0, 600.0, "jomashop", "Watches", self.forex_rate, vendor="Seiko")
        self.assertEqual(p_drop, 38799.0)
        self.assertEqual(comp_drop, 56999.0)
        self.assertLess(p_drop, p_orig)

        # Supplier price spikes to $500, MSRP $600 -> 16.67% discount -> 16% markup: 500 * 95 * 1.16 = 55100 -> 55099
        # (capped at MSRP ceiling: 600 * 95 = 57000 -> 56999)
        p_spike, comp_spike = resolve_storefront_pricing(500.0, 600.0, "jomashop", "Watches", self.forex_rate, vendor="Seiko")
        self.assertEqual(p_spike, 55099.0)
        self.assertGreater(p_spike, p_orig)
        self.assertLessEqual(p_spike, comp_spike)

    def test_freshner_delta_apply_and_payload_generation(self):
        from stores.jomashop.delta import apply_delta_to_product

        mock_watch = {
            "id": "seiko_test_001",
            "source_store": "jomashop",
            "vendor": "Seiko",
            "product_type": "Watches",
            "title": "Seiko Prospex Automatic",
            "source_sku": "SKX007",
            "source_price": 300.0,
            "source_compare_at_price": 600.0,
            "current_price": 28500.0,
            "availability": "in_stock",
            "variants": [
                {
                    "sku": "SKX007-BLUE",
                    "title": "Blue Dial",
                    "color": "Blue",
                    "source_price": 300.0,
                    "source_compare_at_price": 600.0,
                    "in_stock": True
                },
                {
                    "sku": "SKX007-BLACK",
                    "title": "Black Dial",
                    "color": "Black",
                    "source_price": 320.0,
                    "source_compare_at_price": 600.0,
                    "in_stock": True
                }
            ]
        }

        # Simulate freshner poll delta result where Blue drops to $240 and Black drops to $280
        delta_res = {
            "status": "success",
            "current_source_price": 240.0,
            "current_compare_at_price": 600.0,
            "availability": "in_stock",
            "price_changed": True,
            "stock_changed": False,
            "variant_price_changed": True,
            "variants_delta": [
                {"sku": "SKX007-BLUE", "price_usd": 240.0, "available": True},
                {"sku": "SKX007-BLACK", "price_usd": 280.0, "available": True}
            ],
            "changed_variant_prices": [
                {"sku": "SKX007-BLUE", "old_source_price": 300.0, "new_source_price": 240.0},
                {"sku": "SKX007-BLACK", "old_source_price": 320.0, "new_source_price": 280.0}
            ]
        }

        # 1. Apply delta to product
        updated_prod, has_changed = apply_delta_to_product(copy.deepcopy(mock_watch), delta_res, self.forex_rate)
        self.assertTrue(has_changed)

        # Invariant: Raw source_price in USD is preserved, never overwritten with INR
        self.assertEqual(updated_prod["source_price"], 240.0)
        self.assertEqual(updated_prod["variants"][0]["source_price"], 240.0)
        self.assertEqual(updated_prod["variants"][1]["source_price"], 280.0)

        # 2. Generate Shopify storefront payload
        payload = prepare_product_set_payload(updated_prod, self.forex_rate)
        variants = payload.get("variants", [])
        self.assertEqual(len(variants), 2)

        v_blue = next(v for v in variants if "SKX007-BLUE" in v["sku"])
        v_black = next(v for v in variants if "SKX007-BLACK" in v["sku"])

        # Blue: $240 vs $600 -> 60% discount -> 70% markup: 240 * 95 * 1.70 = 38760 -> 38799
        self.assertEqual(float(v_blue["price"]), 38799.0)

        # Black: $280 vs $600 -> 53.33% discount -> 50% markup: 280 * 95 * 1.50 = 39900 -> 39899
        self.assertEqual(float(v_black["price"]), 39899.0)

        # Both variants end in .99
        self.assertEqual(int(float(v_blue["price"])) % 100, 99)
        self.assertEqual(int(float(v_black["price"])) % 100, 99)

    def test_freshner_poll_single_product_dry_run_attaches_storefront_prices(self):
        """Verify that poll_single_product attaches new_storefront_price_inr even in dry-run mode."""
        from sync_catalog import poll_single_product

        class MockJomashopFluctuatingStoreMod:
            @staticmethod
            def check_price_and_stock(product, **kwargs):
                return {
                    "status": "success",
                    "current_source_price": 240.0,
                    "current_compare_at_price": 600.0,
                    "availability": "in_stock",
                    "price_changed": True,
                    "variant_price_changed": True,
                    "changed_variant_prices": [
                        {
                            "sku": "TIST0992072211802",
                            "old_source_price": 329.0,
                            "new_source_price": 240.0,
                            "source_compare_at_price": 600.0
                        }
                    ]
                }

            @staticmethod
            def apply_delta_to_product(product, delta_res, fx):
                return product, True

        stub = {"id": "009e74a980966b3c", "store": "jomashop", "handle": "tissot-watch-t099-207-22-118-02"}
        delta_res = poll_single_product(stub, MockJomashopFluctuatingStoreMod, dry_run=True, forex_rate=95.0)

        # Invariant: new_storefront_price_inr is attached to delta_res and variant shifts
        self.assertIn("new_storefront_price_inr", delta_res)
        # 240 vs 600 -> 60% discount -> 70% markup: 240 * 95 * 1.70 = 38760 -> 38799
        self.assertEqual(delta_res["new_storefront_price_inr"], 38799.0)

        cvp_list = delta_res.get("changed_variant_prices", [])
        self.assertEqual(len(cvp_list), 1)
        self.assertIn("new_storefront_price_inr", cvp_list[0])
        self.assertEqual(cvp_list[0]["new_storefront_price_inr"], 38799.0)


if __name__ == "__main__":
    unittest.main()
