"""
Milestone M1 Empirical Adversarial Challenge Test Suite
Thoroughly stress-tests:
1. Availability Cascade Stress Testing (Coach & JW PEI apply_delta_to_product)
   - Empty variants, None fields, malformed variant objects, integer SKUs, status transitions.
2. Variant Size Run & Pricing Boundary Stress Testing
   - Sizing truncation detection, Coach multi-price integrity, whole-rupee INR rounding boundaries.
3. Live Sampling Network Fault Robustness
   - HTTP timeouts, 429 rate limits, 404 delistings, and exception handling in audit_cross_brand_catalog.py.
"""
import copy
import json
import os
import sys
import time
from typing import Dict, Any, List, Tuple
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from stores.coach.delta import apply_delta_to_product as coach_apply_delta
from stores.jwpei.delta import apply_delta_to_product as jwpei_apply_delta
from scripts.audit_cross_brand_catalog import (
    audit_footwear_and_apparel_sizing,
    audit_coach_multi_price_variants,
    audit_handbags_accessories_and_inr_math,
    run_live_pdp_sampling_audit
)


def run_test(test_name: str, test_fn):
    print(f"\n{'='*75}")
    print(f"RUNNING TEST: {test_name}")
    print(f"{'='*75}")
    t0 = time.perf_counter()
    try:
        passed, details = test_fn()
        elapsed = (time.perf_counter() - t0) * 1000
        if passed:
            print(f"[PASS] {test_name} ({elapsed:.1f}ms): {details}")
            return True, details
        else:
            print(f"[FAIL] {test_name} ({elapsed:.1f}ms): {details}")
            return False, details
    except Exception as e:
        elapsed = (time.perf_counter() - t0) * 1000
        print(f"[CRASH/FAIL] {test_name} ({elapsed:.1f}ms): Exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Exception: {type(e).__name__}: {e}"


# ==============================================================================
# SECTION 1: AVAILABILITY CASCADE STRESS TESTING
# ==============================================================================

def test_coach_availability_cascade_valid_oos():
    """Test standard availability cascade when Coach product flips to out_of_stock."""
    product = {
        "handle": "test-coach-bag",
        "source_price": 350.0,
        "current_price": 29400.0,
        "availability": "in_stock",
        "is_active": True,
        "variants": [
            {"sku": "SKU-BLK", "in_stock": True, "source_price": 350.0},
            {"sku": "SKU-BRN", "in_stock": True, "source_price": 350.0}
        ]
    }
    delta = {
        "status": "success",
        "stock_changed": True,
        "availability": "out_of_stock",
        "current_source_price": 350.0,
        "variants_delta": []
    }
    updated, has_changed = coach_apply_delta(copy.deepcopy(product), delta, forex_rate=84.0)
    assert has_changed is True, "has_changed should be True"
    assert updated["availability"] == "out_of_stock", f"Expected out_of_stock, got {updated['availability']}"
    assert updated["is_active"] is False, f"Expected is_active=False, got {updated['is_active']}"
    for v in updated["variants"]:
        assert v["in_stock"] is False, f"Variant {v['sku']} in_stock should be False"
    assert updated.get("shopify_sync_pending") is True, "shopify_sync_pending should be True"
    return True, "Standard Coach OOS cascade correctly marks all child variants out_of_stock."


def test_jwpei_availability_cascade_valid_oos():
    """Test standard availability cascade when JW PEI product flips to out_of_stock."""
    product = {
        "handle": "test-jwpei-bag",
        "source_price": 89.0,
        "current_price": 7476.0,
        "availability": "in_stock",
        "is_active": True,
        "variants": [
            {"sku": "JW-V1", "in_stock": True, "is_available": True, "price_current": 7476.0},
            {"sku": "JW-V2", "in_stock": True, "is_available": True, "price_current": 7476.0}
        ]
    }
    delta = {
        "status": "success",
        "stock_changed": True,
        "availability": "out_of_stock",
        "current_source_price": 89.0,
        "variants_delta": []
    }
    updated, has_changed = jwpei_apply_delta(copy.deepcopy(product), delta, forex_rate=84.0)
    assert has_changed is True, "has_changed should be True"
    assert updated["availability"] == "out_of_stock", f"Expected out_of_stock, got {updated['availability']}"
    assert updated["is_active"] is False, f"Expected is_active=False, got {updated['is_active']}"
    for v in updated["variants"]:
        assert v["in_stock"] is False, f"Variant {v['sku']} in_stock should be False"
        assert v.get("is_available") is False, f"Variant {v['sku']} is_available should be False"
    assert updated.get("shopify_sync_pending") is True, "shopify_sync_pending should be True"
    return True, "Standard JW PEI OOS cascade correctly synchronizes in_stock and is_available to False."


def test_availability_cascade_delisted_status():
    """Test availability cascade when status flips to delisted."""
    for store, apply_fn in [("Coach", coach_apply_delta), ("JW PEI", jwpei_apply_delta)]:
        product = {
            "handle": f"test-{store.lower()}-delist",
            "source_price": 100.0,
            "availability": "in_stock",
            "is_active": True,
            "variants": [{"sku": "SKU-1", "in_stock": True, "is_available": True}]
        }
        delta = {
            "status": "not_found",
            "availability": "delisted",
            "stock_changed": True,
            "variants_delta": []
        }
        updated, has_changed = apply_fn(copy.deepcopy(product), delta, forex_rate=84.0)
        assert has_changed is True, f"[{store}] has_changed should be True"
        assert updated["availability"] == "delisted" or updated["availability"] == "out_of_stock"
        assert updated["is_active"] is False
        assert updated["variants"][0]["in_stock"] is False, f"[{store}] variant in_stock should be False"
        if "is_available" in updated["variants"][0]:
            assert updated["variants"][0]["is_available"] is False
    return True, "Both stores successfully cascade delisted status to child variants."


def test_availability_cascade_empty_and_none_variants():
    """Stress test when product has empty variants list, None variants, or missing variants key."""
    for store, apply_fn in [("Coach", coach_apply_delta), ("JW PEI", jwpei_apply_delta)]:
        # Case A: empty variants list []
        p_empty = {"handle": "p_empty", "source_price": 100.0, "availability": "in_stock", "variants": []}
        delta = {"status": "success", "stock_changed": True, "availability": "out_of_stock", "variants_delta": []}
        u, ch = apply_fn(copy.deepcopy(p_empty), delta, 84.0)
        assert ch is True and u["availability"] == "out_of_stock"

        # Case B: variants is None
        p_none = {"handle": "p_none", "source_price": 100.0, "availability": "in_stock", "variants": None}
        u, ch = apply_fn(copy.deepcopy(p_none), delta, 84.0)
        assert ch is True and u["availability"] == "out_of_stock"

        # Case C: no variants key
        p_nokey = {"handle": "p_nokey", "source_price": 100.0, "availability": "in_stock"}
        u, ch = apply_fn(copy.deepcopy(p_nokey), delta, 84.0)
        assert ch is True and u["availability"] == "out_of_stock"

    return True, "Both stores safely handle products with empty variants, None variants, and missing variant keys without throwing exceptions."


def test_availability_cascade_malformed_variant_objects():
    """Stress test when variant objects have missing keys, None values, non-dict types, or unexpected structures."""
    malformed_variants = [
        {},  # empty dict
        {"sku": None, "in_stock": None},  # None values
        {"sku": "SKU-EMPTY-STOCK"},  # missing in_stock
        {"sku": 12345, "in_stock": True},  # integer SKU
        {"sku": "SKU-STR-BOOL", "in_stock": "yes", "is_available": "true"},  # non-boolean values
        {"title": "Size 8", "in_stock": True}  # missing SKU, title only
    ]
    delta = {"status": "success", "stock_changed": True, "availability": "out_of_stock", "variants_delta": []}

    for store, apply_fn in [("Coach", coach_apply_delta), ("JW PEI", jwpei_apply_delta)]:
        product = {
            "handle": f"test-malformed-{store}",
            "source_price": 50.0,
            "availability": "in_stock",
            "variants": copy.deepcopy(malformed_variants)
        }
        updated, has_changed = apply_fn(product, delta, 84.0)
        assert has_changed is True
        assert updated["availability"] == "out_of_stock"
        for idx, v in enumerate(updated["variants"]):
            assert v.get("in_stock") is False, f"[{store}] variant {idx} in_stock was not False: {v}"

    return True, "Malformed variant dicts (None, missing keys, int SKUs) safely handled by cascade."


def test_availability_cascade_restock_behavior():
    """
    CRITICAL EDGE CASE:
    What happens when an out_of_stock product restocks to in_stock, but variants_delta is empty?
    e.g. single-variant item or non-sized accessory where PDP returns in_stock without child breakdown.
    Does the parent availability become in_stock while variants remain in_stock: False?
    """
    product = {
        "handle": "handbag-restock-test",
        "source_price": 200.0,
        "current_price": 16800.0,
        "availability": "out_of_stock",
        "is_active": False,
        "variants": [
            {"sku": "BAG-001", "in_stock": False, "is_available": False, "source_price": 200.0, "price": "16800.00"}
        ]
    }
    # Restock event without variant breakdown
    delta = {
        "status": "success",
        "stock_changed": True,
        "availability": "in_stock",
        "is_active": True,
        "current_source_price": 200.0,
        "variants_delta": []
    }

    coach_res, coach_changed = coach_apply_delta(copy.deepcopy(product), delta, 84.0)
    jwpei_res, jwpei_changed = jwpei_apply_delta(copy.deepcopy(product), delta, 84.0)

    coach_variant_stock = coach_res["variants"][0].get("in_stock")
    jwpei_variant_stock = jwpei_res["variants"][0].get("in_stock")

    coach_desync = (coach_res["availability"] == "in_stock" and coach_variant_stock is False)
    jwpei_desync = (jwpei_res["availability"] == "in_stock" and jwpei_variant_stock is False)

    if coach_desync or jwpei_desync:
        return False, (
            f"VULNERABILITY DETECTED: Availability restock desynchronization!\n"
            f"  Coach parent availability: '{coach_res['availability']}', variant in_stock: {coach_variant_stock} (desync: {coach_desync})\n"
            f"  JW PEI parent availability: '{jwpei_res['availability']}', variant in_stock: {jwpei_variant_stock} (desync: {jwpei_desync})\n"
            f"  When a product transitions out_of_stock -> in_stock with variants_delta=[], parent flips to in_stock but variants remain False!"
        )

    return True, "Restock without variant diffs correctly synchronized variant in_stock."


def test_availability_cascade_error_and_rate_limit_immutability():
    """Verify that transient status ('error', 'rate_limited') does NOT mutate product data or stamp last_verified_at."""
    initial_product = {
        "handle": "protected-prod",
        "source_price": 150.0,
        "current_price": 12600.0,
        "availability": "in_stock",
        "is_active": True,
        "last_verified_at": "2026-09-01T00:00:00Z",
        "variants": [{"sku": "P-1", "in_stock": True, "source_price": 150.0}]
    }

    for status in ("error", "rate_limited", "timeout"):
        delta = {
            "status": status,
            "availability": "out_of_stock",
            "current_source_price": 999.0,
            "stock_changed": True,
            "price_changed": True,
            "variants_delta": []
        }
        for store, apply_fn in [("Coach", coach_apply_delta), ("JW PEI", jwpei_apply_delta)]:
            p_copy = copy.deepcopy(initial_product)
            updated, has_changed = apply_fn(p_copy, delta, 84.0)
            assert has_changed is False, f"[{store}] has_changed must be False for {status}"
            assert updated["source_price"] == 150.0, f"[{store}] price was mutated on {status}"
            assert updated["availability"] == "in_stock", f"[{store}] availability was mutated on {status}"
            assert updated["last_verified_at"] == "2026-09-01T00:00:00Z", f"[{store}] last_verified_at was stamped on {status}"
            assert updated["variants"][0]["in_stock"] is True, f"[{store}] variant stock was mutated on {status}"

    return True, "Both stores strictly preserve product immutability on non-success/non-404 status."


# ==============================================================================
# SECTION 2: VARIANT SIZE RUN & PRICING BOUNDARY STRESS TESTING
# ==============================================================================

def test_audit_catches_apparel_truncation():
    """Verify audit_footwear_and_apparel_sizing catches synthetic truncated apparel products."""
    mock_catalog = {
        'coach': [
            {
                'product_id': 'coach-shoe-1',
                'handle': 'coach-shoe-1',
                'groups': ['shoes', 'women_shoes'],
                'product_type': 'Shoes',
                'variants': [{'sku': 'S1', 'title': '7'}]  # <= 1 variant: TRUNCATED!
            }
        ],
        'michaelkors': [],
        'jwpei': [],
        'nordstrom': []
    }
    try:
        audit_footwear_and_apparel_sizing(mock_catalog)
        return False, "Failed to catch footwear product with only 1 variant!"
    except AssertionError as e:
        return True, f"Correctly caught truncated footwear product via assertion: {e}"


def test_audit_catches_none_variants_in_sizing():
    """Verify audit_footwear_and_apparel_sizing handles variants=None without crash."""
    mock_catalog = {
        'coach': [
            {
                'product_id': 'coach-shoe-null',
                'handle': 'coach-shoe-null',
                'groups': ['shoes'],
                'product_type': 'Shoes',
                'variants': None  # None variants!
            }
        ],
        'michaelkors': [],
        'jwpei': [],
        'nordstrom': []
    }
    try:
        audit_footwear_and_apparel_sizing(mock_catalog)
        return False, "Expected assertion or truncation detection, did not raise."
    except TypeError as te:
        return False, f"VULNERABILITY: audit_footwear_and_apparel_sizing crashes with TypeError when variants is None: {te}"
    except AssertionError:
        return True, "Audit caught None variants as truncated without crashing."


def test_audit_catches_coach_multi_price_discrepancies():
    """Verify audit_coach_multi_price_variants catches missing SKUs, invalid images, and zero prices."""
    # Test A: Missing SKU
    catalog_bad_sku = {
        'coach': [
            {
                'handle': 'multi-sku-fail',
                'variants': [
                    {'sku': '', 'source_price': 200.0, 'price': '16800.00', 'image_url': 'https://coach.scene7.com/img1'},
                    {'sku': 'SKU2', 'source_price': 300.0, 'price': '25200.00', 'image_url': 'https://coach.scene7.com/img2'}
                ]
            }
        ] * 280
    }
    try:
        audit_coach_multi_price_variants(catalog_bad_sku)
        return False, "Failed to catch missing SKU in multi-price Coach product!"
    except AssertionError as e:
        pass

    # Test B: Invalid image url
    catalog_bad_img = {
        'coach': [
            {
                'handle': 'multi-img-fail',
                'variants': [
                    {'sku': 'SKU1', 'source_price': 200.0, 'price': '16800.00', 'image_url': 'https://example.com/bad.jpg'},
                    {'sku': 'SKU2', 'source_price': 300.0, 'price': '25200.00', 'image_url': 'https://coach.scene7.com/img2'}
                ]
            }
        ] * 280
    }
    try:
        audit_coach_multi_price_variants(catalog_bad_img)
        return False, "Failed to catch non-Scene7 image in multi-price Coach product!"
    except AssertionError as e:
        pass

    # Test C: Zero or negative price
    catalog_bad_price = {
        'coach': [
            {
                'handle': 'multi-price-fail',
                'variants': [
                    {'sku': 'SKU1', 'source_price': 0.0, 'price': '0.00', 'image_url': 'https://coach.scene7.com/img1'},
                    {'sku': 'SKU2', 'source_price': 300.0, 'price': '25200.00', 'image_url': 'https://coach.scene7.com/img2'}
                ]
            }
        ] * 280
    }
    try:
        audit_coach_multi_price_variants(catalog_bad_price)
        return False, "Failed to catch invalid/zero price in multi-price Coach product!"
    except AssertionError as e:
        pass

    return True, "audit_coach_multi_price_variants strictly asserts SKU, Scene7 URL, and positive pricing integrity."


def test_audit_catches_fractional_inr_paise():
    """Verify audit_handbags_accessories_and_inr_math catches fractional paise in parent and variant prices."""
    # Test parent fractional INR
    bad_parent = {
        'coach': [{
            'current_price': 19999.50,  # fractional!
            'availability': 'in_stock',
            'variants': [{'sku': 'V1', 'price': '20000.00', 'in_stock': True}]
        }]
    }
    try:
        audit_handbags_accessories_and_inr_math(bad_parent)
        return False, "Failed to catch fractional parent INR price!"
    except AssertionError as e:
        pass

    # Test variant fractional INR
    bad_variant = {
        'coach': [{
            'current_price': 20000.0,
            'availability': 'in_stock',
            'variants': [{'sku': 'V1', 'price': '20000.75', 'in_stock': True}]  # fractional!
        }]
    }
    try:
        audit_handbags_accessories_and_inr_math(bad_variant)
        return False, "Failed to catch fractional variant INR price!"
    except AssertionError as e:
        pass

    return True, "audit_handbags_accessories_and_inr_math strictly flags any fractional paise prices."


def test_inr_math_rounding_boundaries():
    """
    Stress-test whole-rupee INR rounding across extreme inputs:
    fractional cents, half-way rounding, tiny prices, huge prices, extreme exchange rates.
    """
    forex_rates = [83.95, 84.0, 84.125, 85.0001]
    test_usd_prices = [
        0.001, 0.005, 0.009, 0.49, 0.50, 0.51, 0.99,
        1.00, 1.005, 12.345, 99.999, 123.456, 499.50, 9999.99, 100000.0
    ]

    failures = []
    for fx in forex_rates:
        for usd in test_usd_prices:
            # 1. Test Coach delta rounding
            prod_c = {"source_price": 10.0, "current_price": 840.0, "availability": "in_stock", "variants": []}
            delta_c = {"status": "success", "price_changed": True, "current_source_price": usd}
            up_c, _ = coach_apply_delta(prod_c, delta_c, forex_rate=fx)
            cp_c = up_c["current_price"]
            if not isinstance(cp_c, (int, float)) or not float(cp_c).is_integer():
                failures.append(f"Coach current_price not whole rupee: usd={usd}, fx={fx}, result={cp_c}")

            # 2. Test JW PEI delta rounding
            prod_jw = {"source_price": 10.0, "current_price": 840.0, "availability": "in_stock", "variants": [
                {"sku": "JW-1", "price_current": 840.0, "price": "840.00"}
            ]}
            delta_jw = {
                "status": "success", "price_changed": True, "current_source_price": usd,
                "variants_delta": [{"sku": "JW-1", "available": True, "price_usd": usd}]
            }
            up_jw, _ = jwpei_apply_delta(prod_jw, delta_jw, forex_rate=fx)
            cp_jw = up_jw["current_price"]
            vp_jw = up_jw["variants"][0]["price_current"]
            vps_jw = float(up_jw["variants"][0]["price"])
            if not float(cp_jw).is_integer():
                failures.append(f"JW PEI current_price not whole rupee: usd={usd}, fx={fx}, result={cp_jw}")
            if not float(vp_jw).is_integer():
                failures.append(f"JW PEI variant price_current not whole rupee: usd={usd}, fx={fx}, result={vp_jw}")
            if not vps_jw.is_integer():
                failures.append(f"JW PEI variant price str not whole rupee: usd={usd}, fx={fx}, result={vps_jw}")

    if failures:
        return False, f"Whole-rupee rounding failed on {len(failures)} cases:\n" + "\n".join(failures[:5])
    return True, f"Whole-rupee INR rounding verified 100% across {len(forex_rates) * len(test_usd_prices)} boundary cases."


# ==============================================================================
# SECTION 3: LIVE SAMPLING NETWORK FAULT ROBUSTNESS
# ==============================================================================

def test_live_sampling_on_http_timeout_and_error():
    """
    CRITICAL CHALLENGE:
    How does run_live_pdp_sampling_audit behave when store checkers encounter
    HTTP timeouts, connection errors, or rate limits?
    Does it report 100% parity falsely because error responses fall back to old values?
    """
    mock_catalog = {
        'coach': [
            {'handle': 'coach-p1', 'source_url': 'https://coach.com/p1', 'source_price': 250.0, 'availability': 'in_stock', 'current_price': 21000.0, 'variants': [{'sku': 'C1'}]}
        ],
        'michaelkors': [
            {'handle': 'mk-p1', 'source_url': 'https://michaelkors.com/p1', 'source_price': 198.0, 'availability': 'in_stock', 'current_price': 16632.0, 'variants': [{'sku': 'M1'}]}
        ],
        'jwpei': [
            {'handle': 'jw-p1', 'source_url': 'https://jwpei.com/p1', 'source_price': 89.0, 'availability': 'in_stock', 'current_price': 7476.0, 'variants': [{'sku': 'J1'}]}
        ]
    }

    # Simulate network timeout / error on all checkers
    def mock_timeout_check(product, **kwargs):
        return {
            "status": "error",
            "handle": product.get("handle"),
            "availability": product.get("availability"),
            "old_availability": product.get("availability"),
            "current_source_price": product.get("source_price"),
            "old_source_price": product.get("source_price"),
            "is_active": product.get("availability") == "in_stock",
            "price_changed": False,
            "stock_changed": False,
            "elapsed_ms": 10000.0,
            "error": "HTTP Connection Timeout (10000ms exhausted)"
        }

    with patch('scripts.audit_cross_brand_catalog.coach_check', side_effect=mock_timeout_check), \
         patch('scripts.audit_cross_brand_catalog.mk_check', side_effect=mock_timeout_check), \
         patch('scripts.audit_cross_brand_catalog.jwpei_check', side_effect=mock_timeout_check):

        audit_res = run_live_pdp_sampling_audit(mock_catalog, samples_per_store=1)

        total_sampled = audit_res['total_sampled']
        divergence_count = audit_res['divergence_count']
        records = audit_res['records']

        all_errors = all(r['status'] == 'error' for r in records)
        falsely_passed = (divergence_count == 0 and all_errors)

        if falsely_passed:
            return False, (
                f"VULNERABILITY DETECTED: Live PDP Sampling false-positive on HTTP Timeout!\n"
                f"  All {total_sampled} requests failed with HTTP Timeout (status='error').\n"
                f"  Yet run_live_pdp_sampling_audit reported divergence_count={divergence_count} "
                f"and passed with '100.0% Parity Concordance Rate'!\n"
                f"  Reason: The audit evaluates divergence against live_price/live_avail returned in the error fallback."
            )

    return True, "Audit correctly distinguished network timeouts from genuine retailer parity."


def test_live_sampling_on_http_429_rate_limiting():
    """
    Test how run_live_pdp_sampling_audit handles HTTP 429 rate limiting.
    """
    mock_catalog = {
        'coach': [
            {'handle': 'coach-p1', 'source_url': 'https://coach.com/p1', 'source_price': 250.0, 'availability': 'in_stock', 'current_price': 21000.0, 'variants': [{'sku': 'C1'}]}
        ],
        'michaelkors': [
            {'handle': 'mk-p1', 'source_url': 'https://michaelkors.com/p1', 'source_price': 198.0, 'availability': 'in_stock', 'current_price': 16632.0, 'variants': [{'sku': 'M1'}]}
        ],
        'jwpei': [
            {'handle': 'jw-p1', 'source_url': 'https://jwpei.com/p1', 'source_price': 89.0, 'availability': 'in_stock', 'current_price': 7476.0, 'variants': [{'sku': 'J1'}]}
        ]
    }

    def mock_429_check(product, **kwargs):
        return {
            "status": "rate_limited",
            "handle": product.get("handle"),
            "availability": product.get("availability"),
            "old_availability": product.get("availability"),
            "current_source_price": product.get("source_price"),
            "old_source_price": product.get("source_price"),
            "is_active": product.get("availability") == "in_stock",
            "price_changed": False,
            "stock_changed": False,
            "elapsed_ms": 2500.0,
            "error": "Rate limit retries exhausted (HTTP 429)"
        }

    with patch('scripts.audit_cross_brand_catalog.coach_check', side_effect=mock_429_check), \
         patch('scripts.audit_cross_brand_catalog.mk_check', side_effect=mock_429_check), \
         patch('scripts.audit_cross_brand_catalog.jwpei_check', side_effect=mock_429_check):

        audit_res = run_live_pdp_sampling_audit(mock_catalog, samples_per_store=1)

        total_sampled = audit_res['total_sampled']
        divergence_count = audit_res['divergence_count']
        records = audit_res['records']

        all_rate_limited = all(r['status'] == 'rate_limited' for r in records)
        falsely_passed = (divergence_count == 0 and all_rate_limited)

        if falsely_passed:
            return False, (
                f"VULNERABILITY DETECTED: Live PDP Sampling false-positive on HTTP 429!\n"
                f"  All {total_sampled} requests were HTTP 429 rate limited.\n"
                f"  Yet run_live_pdp_sampling_audit reported divergence_count={divergence_count} "
                f"and passed with '100.0% Parity Concordance Rate'!"
            )

    return True, "Audit correctly handled 429 rate limiting."


def test_live_sampling_on_http_404_delisting():
    """
    Test how run_live_pdp_sampling_audit handles legitimate HTTP 404 delistings.
    Stored item is in_stock, but retailer returns 404 (out_of_stock).
    Should detect this as an availability divergence!
    """
    mock_catalog = {
        'coach': [
            {'handle': 'coach-delisted', 'source_url': 'https://coach.com/delisted', 'source_price': 250.0, 'availability': 'in_stock', 'current_price': 21000.0, 'variants': [{'sku': 'C1'}]}
        ],
        'michaelkors': [],
        'jwpei': []
    }

    def mock_404_check(product, **kwargs):
        return {
            "status": "not_found",
            "handle": product.get("handle"),
            "availability": "out_of_stock",
            "old_availability": product.get("availability"),
            "current_source_price": product.get("source_price"),
            "old_source_price": product.get("source_price"),
            "is_active": False,
            "price_changed": False,
            "stock_changed": True,
            "elapsed_ms": 350.0,
            "message": "Product delisted (HTTP 404)"
        }

    with patch('scripts.audit_cross_brand_catalog.coach_check', side_effect=mock_404_check):
        try:
            run_live_pdp_sampling_audit(mock_catalog, samples_per_store=1)
            return False, "Failed to catch availability divergence when live product returned 404!"
        except AssertionError as e:
            return True, f"Live sampling correctly caught 404 availability divergence and asserted: {e}"


# ==============================================================================
# MAIN TEST RUNNER
# ==============================================================================

def main():
    print("=" * 80)
    print("STARTING EMPIRICAL ADVERSARIAL CHALLENGE SUITE FOR MILESTONE M1")
    print("=" * 80)

    tests = [
        # Section 1: Availability Cascade Stress Testing
        ("1.1 Coach Availability Cascade (Valid OOS)", test_coach_availability_cascade_valid_oos),
        ("1.2 JW PEI Availability Cascade (Valid OOS)", test_jwpei_availability_cascade_valid_oos),
        ("1.3 Delisted Status Cascade (Both Stores)", test_availability_cascade_delisted_status),
        ("1.4 Empty / None / Missing Variants Cascade", test_availability_cascade_empty_and_none_variants),
        ("1.5 Malformed Variant Objects Cascade", test_availability_cascade_malformed_variant_objects),
        ("1.6 Out-of-Stock to In-Stock Restock Cascade", test_availability_cascade_restock_behavior),
        ("1.7 Non-Success Delta Immutability", test_availability_cascade_error_and_rate_limit_immutability),

        # Section 2: Variant Size Run & Pricing Boundary Stress Testing
        ("2.1 Catch Footwear/Apparel Truncations", test_audit_catches_apparel_truncation),
        ("2.2 Catch None Variants in Sizing Audit", test_audit_catches_none_variants_in_sizing),
        ("2.3 Catch Coach Multi-Price Discrepancies", test_audit_catches_coach_multi_price_discrepancies),
        ("2.4 Catch Fractional INR Paise", test_audit_catches_fractional_inr_paise),
        ("2.5 Whole-Rupee INR Rounding Boundaries", test_inr_math_rounding_boundaries),

        # Section 3: Live Sampling Network Fault Robustness
        ("3.1 Live Sampling on HTTP Timeout/Error", test_live_sampling_on_http_timeout_and_error),
        ("3.2 Live Sampling on HTTP 429 Rate Limiting", test_live_sampling_on_http_429_rate_limiting),
        ("3.3 Live Sampling on HTTP 404 Delisting", test_live_sampling_on_http_404_delisting),
    ]

    passed_count = 0
    failed_count = 0
    results_summary = []

    for name, fn in tests:
        ok, msg = run_test(name, fn)
        if ok:
            passed_count += 1
            results_summary.append((name, "PASS", msg))
        else:
            failed_count += 1
            results_summary.append((name, "FAIL", msg))

    print("\n" + "=" * 80)
    print(f"ADVERSARIAL CHALLENGE SUMMARY: {passed_count} PASSED | {failed_count} FAILED")
    print("=" * 80)
    for name, status, msg in results_summary:
        print(f"[{status}] {name}")
        if status == "FAIL":
            for line in msg.strip().split("\n"):
                print(f"       {line}")

    if failed_count > 0:
        print(f"\n[VERDICT: CHALLENGE_FAILED] Found {failed_count} critical failure modes!")
        sys.exit(1)
    else:
        print("\n[VERDICT: APPROVE] All adversarial stress checks passed cleanly!")
        sys.exit(0)


if __name__ == "__main__":
    main()
