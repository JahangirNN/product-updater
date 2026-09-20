"""
Milestone 1 Adversarial Delta Engine Challenge Test Suite
Specifically challenges and stress-tests the JD Sports delta engine contract:
1. Selective Timestamp Stamping Invariant (ADR 0008)
   - Verified that last_verified_at is ONLY updated on 'success' and 'not_found'.
   - Verified that last_verified_at is NEVER updated on 'rate_limited', 'error', None, or transient failures.
2. HTTP 404 Delisting Cascade & State Preservation (ADR 0008, ADR 0010, ADR 0015)
   - Verified variant depletion cascade (in_stock = False for all child variants).
   - Verified parent availability flips to 'out_of_stock' and is_active to False.
   - Verified historical pricing is preserved (never None, null, or zeroed).
   - Verified ghost stock elimination when parent was already out_of_stock.
3. Partial Variant Stock Shifts & Phantom Delta Elimination (ADR 0015)
   - Verified that when 1 of 10 variants changes stock, stock_changed is False (zero phantom events).
   - Verified that variant_stock_changed is True and changed_variants contains exact diffs.
   - Verified Stock Harmony: parent availability == 'in_stock' iff any child variant is in stock.
   - Verified legitimate transitions: 1->0 sets stock_changed=True, 0->1 sets stock_changed=True.
4. Slug Apostrophe Stripping & URL Normalization
   - Verified '07 stripping (e.g. Nike Air Force 1 '07 -> nike-air-force-1-07).
   - Verified 's stripping (e.g. Women's -> womens, Men's -> mens).
   - Verified Unicode curly apostrophes (\\u2019s -> s).
   - Verified plural possessive apostrophes (Girls', Boys').
   - Verified URL slug generation without double hyphens, broken punctuation, or leading/trailing hyphens.
5. Rate Limiter, Circuit Breaker & 429/403 Handling
   - Verified rate limiter permit acquisition.
   - Verified HTTP 429 trips circuit breaker and returns status='rate_limited'.
   - Verified HTTP 403 Akamai WAF returns status='rate_limited'.
6. Whole-Rupee INR Math & Currency Harmony (ADR 0006)
   - Verified whole-rupee math on price updates (current_price.is_integer() == True).
"""
import copy
import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Tuple
from unittest.mock import MagicMock, patch
import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from stores.jdsports.delta import (
    check_price_and_stock,
    apply_delta_to_product
)
from stores.jdsports.inflow import (
    classify_sizing_category,
    parse_and_format_size,
    parse_product_payload
)
from storage.rate_limiter import (
    reset_rate_limiter,
    is_circuit_open,
    configure_store_rate_limits
)


def run_test_case(name: str, fn) -> Tuple[bool, str]:
    print(f"\n{'='*75}")
    print(f"RUNNING TEST: {name}")
    print(f"{'='*75}")
    t0 = time.perf_counter()
    try:
        ok, msg = fn()
        elapsed = (time.perf_counter() - t0) * 1000
        if ok:
            print(f"  [PASS] {name} ({elapsed:.1f}ms): {msg}")
            return True, msg
        else:
            print(f"  [FAIL] {name} ({elapsed:.1f}ms): {msg}")
            return False, msg
    except Exception as e:
        elapsed = (time.perf_counter() - t0) * 1000
        print(f"  [CRASH] {name} ({elapsed:.1f}ms): Exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Exception: {type(e).__name__}: {e}"


# ==============================================================================
# SECTION 1: SELECTIVE TIMESTAMP STAMPING INVARIANT (ADR 0008)
# ==============================================================================

def test_selective_timestamp_on_rate_limited():
    """Verify last_verified_at is NEVER updated when status is 'rate_limited'."""
    initial_ts = "2026-09-18T12:00:00Z"
    product = {
        "id": "prod_test_01",
        "title": "Nike Air Force 1 '07",
        "source_price": 115.0,
        "current_price": 9660.0,
        "availability": "in_stock",
        "is_active": True,
        "last_verified_at": initial_ts,
        "variants": [{"sku": "SKU-01", "in_stock": True, "source_price": 115.0}]
    }
    delta_result = {
        "status": "rate_limited",
        "error": "Akamai Bot Manager 403 Forbidden",
        "stock_changed": False,
        "variant_stock_changed": False,
        "price_changed": False
    }

    updated, has_changed = apply_delta_to_product(copy.deepcopy(product), delta_result, forex_rate=84.0)

    assert has_changed is False, "has_changed must be False on rate_limited"
    assert updated["last_verified_at"] == initial_ts, (
        f"last_verified_at was modified on rate_limited: expected {initial_ts}, got {updated['last_verified_at']}"
    )
    assert updated.get("shopify_sync_pending") is not True, "shopify_sync_pending must NOT be set"
    return True, "last_verified_at remains completely untouched on 'rate_limited' status."


def test_selective_timestamp_on_error():
    """Verify last_verified_at is NEVER updated when status is 'error'."""
    initial_ts = "2026-09-18T10:30:00Z"
    product = {
        "id": "prod_test_02",
        "title": "Nike Dunk Low Retro",
        "source_price": 115.0,
        "current_price": 9660.0,
        "availability": "in_stock",
        "is_active": True,
        "last_verified_at": initial_ts,
        "variants": [{"sku": "SKU-02", "in_stock": True, "source_price": 115.0}]
    }
    delta_result = {
        "status": "error",
        "error": "ConnectTimeout: [Errno 11001] getaddrinfo failed",
        "stock_changed": False,
        "variant_stock_changed": False,
        "price_changed": False
    }

    updated, has_changed = apply_delta_to_product(copy.deepcopy(product), delta_result, forex_rate=84.0)

    assert has_changed is False, "has_changed must be False on error"
    assert updated["last_verified_at"] == initial_ts, (
        f"last_verified_at was modified on error: expected {initial_ts}, got {updated['last_verified_at']}"
    )
    return True, "last_verified_at remains completely untouched on 'error' status."


def test_selective_timestamp_on_unknown_or_none_status():
    """Verify last_verified_at is NEVER updated on arbitrary or null statuses."""
    initial_ts = "2026-09-18T08:00:00Z"
    product = {
        "id": "prod_test_03",
        "title": "Nike Air Max 90",
        "source_price": 130.0,
        "current_price": 10920.0,
        "availability": "in_stock",
        "is_active": True,
        "last_verified_at": initial_ts,
        "variants": [{"sku": "SKU-03", "in_stock": True, "source_price": 130.0}]
    }

    for bad_status in [None, "unknown", "timeout", "network_failure", ""]:
        delta_result = {"status": bad_status}
        updated, has_changed = apply_delta_to_product(copy.deepcopy(product), delta_result, forex_rate=84.0)
        assert has_changed is False
        assert updated["last_verified_at"] == initial_ts, f"Failed on bad status {bad_status}"

    return True, "Arbitrary and null statuses safely rejected without timestamp modification."


def test_selective_timestamp_on_success():
    """Verify last_verified_at IS updated on 'success'."""
    initial_ts = "2026-09-18T10:00:00Z"
    product = {
        "id": "prod_test_04",
        "title": "Nike Air Max 90",
        "source_price": 130.0,
        "current_price": 10920.0,
        "availability": "in_stock",
        "is_active": True,
        "last_verified_at": initial_ts,
        "variants": [{"sku": "SKU-04", "in_stock": True, "source_price": 130.0}]
    }
    delta_result = {
        "status": "success",
        "current_source_price": 130.0,
        "availability": "in_stock",
        "price_changed": False,
        "stock_changed": False,
        "variant_stock_changed": False,
        "variants_delta": [{"sku": "SKU-04", "available": True, "price_usd": 130.0}]
    }

    updated, has_changed = apply_delta_to_product(copy.deepcopy(product), delta_result, forex_rate=84.0)

    assert updated["last_verified_at"] != initial_ts, "last_verified_at MUST be updated on success"
    assert updated["last_verified_at"].endswith("Z"), "Timestamp must be UTC ISO-8601 string"
    assert has_changed is False, "has_changed should be False when no price/stock changed"
    return True, "last_verified_at successfully stamped on 'success' without spurious mutation."


def test_selective_timestamp_on_not_found():
    """Verify last_verified_at IS updated on 'not_found' (404 delisting)."""
    initial_ts = "2026-09-18T10:00:00Z"
    product = {
        "id": "prod_test_05",
        "title": "Nike Air Max 90",
        "source_price": 130.0,
        "current_price": 10920.0,
        "availability": "in_stock",
        "is_active": True,
        "last_verified_at": initial_ts,
        "variants": [{"sku": "SKU-05", "in_stock": True, "source_price": 130.0}]
    }
    delta_result = {
        "status": "not_found",
        "availability": "out_of_stock",
        "current_source_price": 130.0,
        "price_changed": False,
        "stock_changed": True,
        "variant_stock_changed": True,
        "variants_delta": []
    }

    updated, has_changed = apply_delta_to_product(copy.deepcopy(product), delta_result, forex_rate=84.0)

    assert updated["last_verified_at"] != initial_ts, "last_verified_at MUST be updated on not_found"
    assert updated["last_verified_at"].endswith("Z")
    assert has_changed is True, "has_changed must be True on 404 delisting"
    return True, "last_verified_at successfully stamped on 'not_found' delistings."


# ==============================================================================
# SECTION 2: HTTP 404 DELISTING CASCADE & PRICE PRESERVATION (ADR 0015)
# ==============================================================================

def test_404_delisting_cascade_and_price_preservation():
    """Verify 404 delisting empties variants stock while strictly preserving historical prices."""
    initial_ts = "2026-09-18T10:00:00Z"
    product = {
        "id": "prod_delist_01",
        "handle": "nike-air-max-90-black-3284880",
        "title": "Nike Air Max 90 - Black",
        "source_price": 130.0,
        "current_price": 10920.0,
        "compare_at_price": 12600.0,
        "source_compare_at_price": 150.0,
        "availability": "in_stock",
        "is_active": True,
        "last_verified_at": initial_ts,
        "variants": [
            {"sku": f"3284880-{i}", "title": f"US {7.0 + i * 0.5}", "in_stock": True, "source_price": 130.0, "price": "10920.00"}
            for i in range(10)
        ]
    }

    # Simulate 404 check_price_and_stock result
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 404

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_resp

    delta_result = check_price_and_stock(product, client=mock_client, store_name="jdsports")

    assert delta_result["status"] == "not_found", f"Expected not_found, got {delta_result['status']}"
    assert delta_result["availability"] == "out_of_stock"
    assert delta_result["is_active"] is False
    assert delta_result["stock_changed"] is True
    assert delta_result["variant_stock_changed"] is True
    assert len(delta_result["changed_variants"]) == 10, f"Expected 10 variant diffs, got {len(delta_result['changed_variants'])}"
    assert delta_result["current_source_price"] == 130.0, "current_source_price must be preserved, not null or zero"
    assert delta_result["old_source_price"] == 130.0
    assert delta_result["price_changed"] is False

    # Apply to product
    updated, has_changed = apply_delta_to_product(copy.deepcopy(product), delta_result, forex_rate=84.0)

    assert has_changed is True, "has_changed must be True"
    assert updated["availability"] == "out_of_stock", f"Expected out_of_stock, got {updated['availability']}"
    assert updated["is_active"] is False, "is_active must be False"
    assert updated["shopify_sync_pending"] is True

    # Check 100% of variants depleted
    for v in updated["variants"]:
        assert v["in_stock"] is False, f"Variant {v['sku']} should have in_stock=False"
        assert v["source_price"] == 130.0, f"Variant {v['sku']} source_price must not be wiped"
        assert v["price"] == "10920.00", f"Variant {v['sku']} price must not be wiped"

    # Check parent pricing preserved
    assert updated["source_price"] == 130.0, "Parent source_price must be preserved"
    assert updated["current_price"] == 10920.0, "Parent current_price must be preserved"
    assert updated["compare_at_price"] == 12600.0, "Parent compare_at_price must be preserved"
    assert updated["last_verified_at"] != initial_ts, "last_verified_at must be updated"

    return True, "404 delisting completely deactivates parent and all 10 variants while preserving 100% of price fields."


def test_404_delisting_ghost_stock_elimination():
    """Verify 404 delisting purges ghost variants when parent was already out_of_stock."""
    product = {
        "id": "prod_ghost_01",
        "title": "Nike Air Force 1 '07",
        "source_price": 115.0,
        "current_price": 9660.0,
        "availability": "out_of_stock",  # Parent is already OOS
        "is_active": False,
        "variants": [
            {"sku": "V-01", "in_stock": False, "source_price": 115.0},
            {"sku": "V-02", "in_stock": True, "source_price": 115.0},   # GHOST STOCK!
            {"sku": "V-03", "in_stock": True, "source_price": 115.0}    # GHOST STOCK!
        ]
    }

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 404
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_resp

    delta = check_price_and_stock(product, client=mock_client, store_name="jdsports")

    assert delta["status"] == "not_found"
    assert delta["stock_changed"] is False, "Top level stock_changed should be False since parent was already OOS"
    assert delta["variant_stock_changed"] is True, "variant_stock_changed must be True to purge ghost variants"
    assert len(delta["changed_variants"]) == 2, f"Expected 2 ghost variant diffs, got {len(delta['changed_variants'])}"

    updated, has_changed = apply_delta_to_product(copy.deepcopy(product), delta, forex_rate=84.0)

    assert has_changed is True, "has_changed must be True when ghost variants are cleaned"
    assert all(v["in_stock"] is False for v in updated["variants"]), "All variants must now be in_stock=False"
    return True, "Ghost stock successfully eliminated and purged on 404 delisting."


def test_404_delisting_idempotency():
    """Verify applying a 404 to an already-depleted product is idempotent (has_changed=False)."""
    product = {
        "id": "prod_depleted_01",
        "title": "Nike Dunk Low",
        "source_price": 115.0,
        "current_price": 9660.0,
        "availability": "out_of_stock",
        "is_active": False,
        "variants": [
            {"sku": "V-01", "in_stock": False, "source_price": 115.0},
            {"sku": "V-02", "in_stock": False, "source_price": 115.0}
        ]
    }

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 404
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_resp

    delta = check_price_and_stock(product, client=mock_client, store_name="jdsports")

    assert delta["status"] == "not_found"
    assert delta["stock_changed"] is False
    assert delta["variant_stock_changed"] is False
    assert delta["changed_variants"] == []

    updated, has_changed = apply_delta_to_product(copy.deepcopy(product), delta, forex_rate=84.0)

    assert has_changed is False, "has_changed must be False when product is already depleted"
    assert updated.get("shopify_sync_pending") is not True
    assert updated["availability"] == "out_of_stock"
    assert updated["is_active"] is False
    return True, "404 delisting is strictly idempotent on already-depleted items."


# ==============================================================================
# SECTION 3: PARTIAL VARIANT STOCK SHIFTS (ZERO PHANTOM EVENTS - ADR 0015)
# ==============================================================================

def _generate_jd_product_with_variants(num_variants: int = 10, all_in_stock: bool = True) -> Dict[str, Any]:
    variants = []
    for i in range(num_variants):
        size_val = 7.0 + (i * 0.5)
        sku_val = f"SKU-{int(size_val * 10)}"
        variants.append({
            "id": None,
            "sku": sku_val,
            "title": f"US {size_val:.1f} / UK {size_val - 1.0:.1f} - White/Black",
            "price": "9660.00",
            "source_price": 115.0,
            "currency": "INR",
            "source_currency": "USD",
            "in_stock": all_in_stock,
            "image_url": "https://media.jdsports.com/i/finishline/SKU_001_P1"
        })
    return {
        "id": "prod_variant_test_01",
        "handle": "nike-air-force-1-07-white-black-sku100",
        "title": "Nike Air Force 1 '07 - White/Black",
        "source_price": 115.0,
        "current_price": 9660.0,
        "availability": "in_stock" if all_in_stock else "out_of_stock",
        "is_active": all_in_stock,
        "variants": variants,
        "source_url": "https://www.jdsports.com/pdp/nike-air-force-1-07/SKU100"
    }


def _generate_jd_jsonld_html(variants_state: List[Tuple[str, float, bool, float]]) -> str:
    """Generate mock JD Sports HTML containing JSON-LD ProductGroup with variants."""
    has_variants = []
    for sku, size_num, is_instock, price_val in variants_state:
        has_variants.append({
            "@type": "Product",
            "sku": sku,
            "size": f"{size_num:.1f}",
            "offers": {
                "@type": "Offer",
                "price": f"{price_val:.2f}",
                "priceCurrency": "USD",
                "availability": "https://schema.org/InStock" if is_instock else "https://schema.org/OutOfStock"
            }
        })

    jsonld_doc = {
        "@context": "https://schema.org",
        "@type": "ProductGroup",
        "name": "Nike Air Force 1 '07",
        "productGroupID": "prod_variant_test_01",
        "hasVariant": has_variants
    }

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <script type="application/ld+json">
      {json.dumps(jsonld_doc)}
      </script>
    </head>
    <body><h1>Nike Air Force 1 '07</h1></body>
    </html>
    """


def test_partial_variant_stock_shift_zero_phantom_event():
    """CRITICAL TEST: When 1 of 10 variants changes stock, stock_changed must be False."""
    product = _generate_jd_product_with_variants(num_variants=10, all_in_stock=True)

    # Variant 3 (size 8.5, sku SKU-85) sells out. The other 9 variants remain in stock.
    live_variants = []
    for v in product["variants"]:
        sku = v["sku"]
        size_num = float(v["title"].split("/")[0].replace("US", "").strip())
        in_stock = False if sku == "SKU-85" else True
        live_variants.append((sku, size_num, in_stock, 115.0))

    html_content = _generate_jd_jsonld_html(live_variants)

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.text = html_content
    mock_resp.raise_for_status = MagicMock()

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_resp

    delta = check_price_and_stock(product, client=mock_client, store_name="jdsports")

    assert delta["status"] == "success"
    # CRITICAL ADR 0015 ASSERTION:
    assert delta["stock_changed"] is False, (
        "PHANTOM EVENT DETECTED! stock_changed must be False when top-level availability remains in_stock!"
    )
    assert delta["variant_stock_changed"] is True, "variant_stock_changed must be True when 1 variant sells out"
    assert len(delta["changed_variants"]) == 1, f"Expected 1 changed variant, got {len(delta['changed_variants'])}"
    assert delta["changed_variants"][0]["sku"] == "SKU-85"
    assert delta["changed_variants"][0]["old_in_stock"] is True
    assert delta["changed_variants"][0]["new_in_stock"] is False
    assert delta["availability"] == "in_stock"

    # Apply to product
    updated, has_changed = apply_delta_to_product(copy.deepcopy(product), delta, forex_rate=84.0)

    assert has_changed is True, "has_changed must be True because variant stock shifted"
    assert updated["availability"] == "in_stock", "Parent availability must remain in_stock"
    assert updated["is_active"] is True
    assert updated["shopify_sync_pending"] is True

    # Verify target variant is False, others are True
    v_map = {v["sku"]: v for v in updated["variants"]}
    assert v_map["SKU-85"]["in_stock"] is False, "Variant SKU-85 in_stock must be False"
    other_variants_stock = [v["in_stock"] for sku, v in v_map.items() if sku != "SKU-85"]
    assert all(other_variants_stock), "All other 9 variants must remain in_stock=True"

    # Verify Stock Harmony ADR 0015:
    expected_parent_avail = "in_stock" if any(v["in_stock"] for v in updated["variants"]) else "out_of_stock"
    assert updated["availability"] == expected_parent_avail, "Parent availability violates Stock Harmony invariant!"

    return True, "Zero phantom event verified: 1 of 10 variant sell-out sets stock_changed=False, variant_stock_changed=True."


def test_partial_variant_restock_zero_phantom_event():
    """Verify that when 1 variant restocks (while others were already in stock), stock_changed is False."""
    product = _generate_jd_product_with_variants(num_variants=10, all_in_stock=True)
    # Start with SKU-85 already out of stock
    for v in product["variants"]:
        if v["sku"] == "SKU-85":
            v["in_stock"] = False

    # Live poll: SKU-85 is now back in stock!
    live_variants = []
    for v in product["variants"]:
        sku = v["sku"]
        size_num = float(v["title"].split("/")[0].replace("US", "").strip())
        live_variants.append((sku, size_num, True, 115.0))

    html_content = _generate_jd_jsonld_html(live_variants)
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.text = html_content
    mock_resp.raise_for_status = MagicMock()
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_resp

    delta = check_price_and_stock(product, client=mock_client, store_name="jdsports")

    assert delta["status"] == "success"
    assert delta["stock_changed"] is False, "stock_changed must be False on variant restock when product was already in_stock"
    assert delta["variant_stock_changed"] is True
    assert len(delta["changed_variants"]) == 1
    assert delta["changed_variants"][0]["sku"] == "SKU-85"
    assert delta["changed_variants"][0]["old_in_stock"] is False
    assert delta["changed_variants"][0]["new_in_stock"] is True

    updated, has_changed = apply_delta_to_product(copy.deepcopy(product), delta, forex_rate=84.0)

    assert has_changed is True
    assert updated["availability"] == "in_stock"
    assert updated["variants"][3]["in_stock"] is True
    return True, "Zero phantom event verified on partial variant restock."


def test_last_variant_sellout_legitimate_transition():
    """Verify that when the last remaining in-stock variant sells out (1 -> 0), stock_changed is True."""
    product = _generate_jd_product_with_variants(num_variants=10, all_in_stock=False)
    # Only SKU-85 is in stock
    for v in product["variants"]:
        if v["sku"] == "SKU-85":
            v["in_stock"] = True
    product["availability"] = "in_stock"
    product["is_active"] = True

    # Live poll: all 10 are now out of stock
    live_variants = []
    for v in product["variants"]:
        sku = v["sku"]
        size_num = float(v["title"].split("/")[0].replace("US", "").strip())
        live_variants.append((sku, size_num, False, 115.0))

    html_content = _generate_jd_jsonld_html(live_variants)
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.text = html_content
    mock_resp.raise_for_status = MagicMock()
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_resp

    delta = check_price_and_stock(product, client=mock_client, store_name="jdsports")

    assert delta["status"] == "success"
    assert delta["stock_changed"] is True, "stock_changed MUST be True when parent availability flips in_stock -> out_of_stock"
    assert delta["variant_stock_changed"] is True
    assert delta["availability"] == "out_of_stock"

    updated, has_changed = apply_delta_to_product(copy.deepcopy(product), delta, forex_rate=84.0)

    assert has_changed is True
    assert updated["availability"] == "out_of_stock"
    assert updated["is_active"] is False
    assert all(v["in_stock"] is False for v in updated["variants"])
    return True, "Legitimate in_stock -> out_of_stock transition correctly records stock_changed=True."


def test_first_variant_restock_legitimate_transition():
    """Verify that when the first variant restocks on an out-of-stock shoe (0 -> 1), stock_changed is True."""
    product = _generate_jd_product_with_variants(num_variants=10, all_in_stock=False)
    product["availability"] = "out_of_stock"
    product["is_active"] = False

    # Live poll: SKU-85 restocks to True!
    live_variants = []
    for v in product["variants"]:
        sku = v["sku"]
        size_num = float(v["title"].split("/")[0].replace("US", "").strip())
        in_stock = True if sku == "SKU-85" else False
        live_variants.append((sku, size_num, in_stock, 115.0))

    html_content = _generate_jd_jsonld_html(live_variants)
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.text = html_content
    mock_resp.raise_for_status = MagicMock()
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_resp

    delta = check_price_and_stock(product, client=mock_client, store_name="jdsports")

    assert delta["status"] == "success"
    assert delta["stock_changed"] is True, "stock_changed MUST be True when parent availability flips out_of_stock -> in_stock"
    assert delta["variant_stock_changed"] is True
    assert delta["availability"] == "in_stock"

    updated, has_changed = apply_delta_to_product(copy.deepcopy(product), delta, forex_rate=84.0)

    assert has_changed is True
    assert updated["availability"] == "in_stock"
    assert updated["is_active"] is True
    assert updated["variants"][3]["in_stock"] is True
    return True, "Legitimate out_of_stock -> in_stock transition correctly records stock_changed=True."


def test_zero_inventory_shift_steady_state():
    """Verify that when no variant stock shifts occur, stock_changed and variant_stock_changed are both False."""
    product = _generate_jd_product_with_variants(num_variants=10, all_in_stock=True)

    live_variants = []
    for v in product["variants"]:
        sku = v["sku"]
        size_num = float(v["title"].split("/")[0].replace("US", "").strip())
        live_variants.append((sku, size_num, True, 115.0))

    html_content = _generate_jd_jsonld_html(live_variants)
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.text = html_content
    mock_resp.raise_for_status = MagicMock()
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_resp

    delta = check_price_and_stock(product, client=mock_client, store_name="jdsports")

    assert delta["status"] == "success"
    assert delta["stock_changed"] is False
    assert delta["variant_stock_changed"] is False
    assert delta["changed_variants"] == []

    updated, has_changed = apply_delta_to_product(copy.deepcopy(product), delta, forex_rate=84.0)

    assert has_changed is False
    assert updated.get("shopify_sync_pending") is not True
    return True, "Steady state verified: zero phantom shifts when inventory is unchanged."


# ==============================================================================
# SECTION 4: SLUG APOSTROPHE STRIPPING & URL NORMALIZATION
# ==============================================================================

def _normalize_title_to_slug(raw_title: str) -> str:
    """Helper applying JD Sports exact normalization rule."""
    cleaned_title = re.sub(r"['\u2019]s\b", "s", raw_title.lower())
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', cleaned_title).strip('-')
    return slug


def test_slug_normalization_apostrophe_stripping():
    """Verify apostrophes in model names ('07, Women's, Men's, curly apostrophes) normalize cleanly."""
    cases = [
        # 1. Nike Air Force 1 '07
        ("Nike Air Force 1 '07", "nike-air-force-1-07"),
        ("Nike Air Force 1 '07 LV8", "nike-air-force-1-07-lv8"),
        ("Nike Air Force 1 '07 Next Nature", "nike-air-force-1-07-next-nature"),

        # 2. Women's / Men's possessives
        ("Women's Nike Air Force 1 '07", "womens-nike-air-force-1-07"),
        ("Men's Nike Dunk Low Retro", "mens-nike-dunk-low-retro"),
        ("Men's Nike Air Max 90", "mens-nike-air-max-90"),

        # 3. Curly Unicode apostrophes (\u2019)
        ("Women’s Nike Air Force 1 ’07", "womens-nike-air-force-1-07"),
        ("Men’s Nike Air Max 95", "mens-nike-air-max-95"),
        ("Nike Dunk Low ’07", "nike-dunk-low-07"),

        # 4. Plural possessives (Girls', Boys')
        ("Girls' Grade School Nike Air Max 90", "girls-grade-school-nike-air-max-90"),
        ("Boys' Little Kids Nike Dunk Low", "boys-little-kids-nike-dunk-low"),
        ("Girls’ Preschool Nike Air Force 1", "girls-preschool-nike-air-force-1"),

        # 5. Boundary cases
        ("'07 Nike Air Force", "07-nike-air-force"),
        ("Nike Air Force 1 '07'", "nike-air-force-1-07"),
        ("Nike Air Max   90 -- Women's !!", "nike-air-max-90-womens"),
        ("Nike Asuna 2 Slide", "nike-asuna-2-slide"),  # 's' inside a word not affected
        ("Men's / Women's Nike Dunk Low", "mens-womens-nike-dunk-low")
    ]

    for raw, expected in cases:
        actual = _normalize_title_to_slug(raw)
        assert actual == expected, f"Normalization mismatch for '{raw}': expected '{expected}', got '{actual}'"

    return True, f"All {len(cases)} slug apostrophe normalization test cases passed with 100% precision."


def test_delta_source_url_generation_from_slug():
    """Verify check_price_and_stock generates clean source_url when missing."""
    product = {
        "id": "prod_url_test",
        "title": "Women's Nike Air Force 1 '07",
        "sku": "DD8959-100",
        "source_price": 115.0,
        "availability": "in_stock",
        "variants": []
        # source_url intentionally omitted
    }

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 404
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_resp

    delta = check_price_and_stock(product, client=mock_client, store_name="jdsports")

    assert delta["status"] == "not_found"
    # Verify the client was called with normalized URL
    called_url = mock_client.get.call_args[0][0]
    expected_url = "https://www.jdsports.com/pdp/womens-nike-air-force-1-07/DD8959-100"
    assert called_url == expected_url, f"Generated source_url mismatch: expected {expected_url}, got {called_url}"

    return True, "check_price_and_stock cleanly constructs canonical URL from slug and SKU without broken apostrophes."


# ==============================================================================
# SECTION 5: RATE LIMITER & CIRCUIT BREAKER ROBUSTNESS
# ==============================================================================

def test_rate_limiter_handling_on_403_and_429():
    """Verify rate limiter permits and circuit breaker integration in check_price_and_stock."""
    product = {
        "id": "prod_rate_test",
        "title": "Nike Air Max 90",
        "sku": "3284880",
        "source_url": "https://www.jdsports.com/pdp/nike-air-max-90/3284880",
        "source_price": 130.0,
        "availability": "in_stock",
        "variants": []
    }

    # Case A: Akamai 403 Forbidden
    mock_resp_403 = MagicMock(spec=httpx.Response)
    mock_resp_403.status_code = 403
    mock_client_403 = MagicMock(spec=httpx.Client)
    mock_client_403.get.return_value = mock_resp_403

    delta_403 = check_price_and_stock(product, client=mock_client_403, store_name="jdsports")
    assert delta_403["status"] == "rate_limited", f"Expected rate_limited on 403, got {delta_403['status']}"

    # Case B: HTTP 429 with Circuit Breaker
    mock_resp_429 = MagicMock(spec=httpx.Response)
    mock_resp_429.status_code = 429
    mock_resp_429.headers = {"Retry-After": "5"}

    mock_client_429 = MagicMock(spec=httpx.Client)
    mock_client_429.get.return_value = mock_resp_429

    mock_limiter = MagicMock()

    with patch("time.sleep", return_value=None):
        delta_429 = check_price_and_stock(product, client=mock_client_429, store_name="jdsports", rate_limiter=mock_limiter)

    assert delta_429["status"] == "rate_limited"
    assert mock_limiter.acquire_permit.called, "rate_limiter.acquire_permit should have been called"
    assert mock_limiter.trip_circuit_breaker.called, "rate_limiter.trip_circuit_breaker should have been called"

    return True, "Rate limiter permits, 403 Akamai handling, and 429 circuit breaker successfully verified."


# ==============================================================================
# SECTION 6: WHOLE-RUPEE INR MATH & CURRENCY HARMONY (ADR 0006)
# ==============================================================================

def test_whole_rupee_inr_math_on_price_shift():
    """Verify price shifts calculate whole-rupee INR values with zero fractional paise."""
    product = _generate_jd_product_with_variants(num_variants=5, all_in_stock=True)
    product["source_price"] = 115.0
    product["current_price"] = 9660.0

    # Price shifts to $129.99 with forex rate 84.37 -> round(129.99 * 84.37) = 10967.0
    delta_result = {
        "status": "success",
        "current_source_price": 129.99,
        "old_source_price": 115.0,
        "price_changed": True,
        "stock_changed": False,
        "variant_stock_changed": False,
        "variants_delta": [
            {"sku": v["sku"], "available": True, "price_usd": 129.99} for v in product["variants"]
        ]
    }

    forex = 84.37
    updated, has_changed = apply_delta_to_product(copy.deepcopy(product), delta_result, forex_rate=forex)

    assert has_changed is True
    expected_inr = float(round(129.99 * forex))
    assert updated["current_price"] == expected_inr
    assert updated["current_price"].is_integer(), "Parent current_price must have zero fractional paise"

    for v in updated["variants"]:
        assert float(v["price"]).is_integer(), f"Variant {v['sku']} price must be whole rupees"
        assert v["price"] == f"{expected_inr:.2f}"
        assert v["source_price"] == 129.99

    return True, "Whole-rupee INR conversion accurately enforced with zero fractional paise."


# ==============================================================================
# SECTION 7: INGESTION SIZING CLASSIFICATION & TOKEN PRESERVATION (ADR 0016)
# ==============================================================================

def test_sizing_category_classification_and_token_preservation():
    """Verify multi-tier sizing category classification and size label preservation."""
    cases = [
        # Toddler
        ("Nike Air Max 90 Toddler Shoes", ["Toddler"], "Toddler", "7", "US 7C", "Toddler 7C disambiguated"),
        ("Nike Dunk Low Infant Shoes", ["Baby"], "Toddler", "10", "US 10C", "Toddler 10C disambiguated"),
        # Preschool
        ("Nike Air Force 1 Little Kids Shoes", ["Little Kids"], "Preschool", "11.5", "US 11.5C", "Preschool 11.5C"),
        ("Nike Air Force 1 Preschool Shoes", ["Preschool"], "Preschool", "2.0", "US 2.0Y", "Preschool 2.0Y"),
        # Grade School
        ("Nike Dunk Low Big Kids Shoes", ["Big Kids"], "Grade School", "7.0", "US 7.0Y", "Youth 7.0Y disambiguated from Adult 7.0"),
        ("Nike Air Max 90 Grade School", ["GS"], "Grade School", "3.5", "US 3.5Y", "Youth 3.5Y"),
        # Adult
        ("Nike Air Force 1 '07 Men's Shoes", ["Adult"], "Adult", "7.0", "US 7.0", "Adult 7.0 disambiguated from Toddler 7C/Youth 7Y"),
        ("Nike Dunk Low Women's Shoes", ["Adult"], "Adult", "8.5", "US 8.5", "Adult Women's 8.5")
    ]

    for title, breadcrumbs, expected_cat, raw_size, expected_label, desc in cases:
        cat = classify_sizing_category(title, breadcrumbs=breadcrumbs)
        assert cat == expected_cat, f"Category classification mismatch for '{title}': expected {expected_cat}, got {cat}"

        label, uk, eu, num_val = parse_and_format_size(raw_size, sizing_category=cat, gender="Men's")
        assert label == expected_label, f"Size formatting mismatch for '{raw_size}' in {cat}: expected {expected_label}, got {label}"

    return True, "Multi-tier sizing classification cleanly disambiguates Adult, GS, PS, and Toddler size tokens."


# ==============================================================================
# MAIN TEST RUNNER
# ==============================================================================

def main():
    print("\n" + "#"*80)
    print("  MILESTONE 1 ADVERSARIAL CHALLENGER 2: JD SPORTS DELTA ENGINE CONTRACT  ")
    print("#"*80)

    tests = [
        # Category 1: Selective Timestamp Stamping
        ("Selective Timestamp Stamping: 'rate_limited' immutability", test_selective_timestamp_on_rate_limited),
        ("Selective Timestamp Stamping: 'error' immutability", test_selective_timestamp_on_error),
        ("Selective Timestamp Stamping: Arbitrary/null status immutability", test_selective_timestamp_on_unknown_or_none_status),
        ("Selective Timestamp Stamping: 'success' updates timestamp", test_selective_timestamp_on_success),
        ("Selective Timestamp Stamping: 'not_found' updates timestamp", test_selective_timestamp_on_not_found),

        # Category 2: HTTP 404 Delisting Cascade & Price Preservation
        ("HTTP 404 Delisting: Variant depletion cascade & price preservation", test_404_delisting_cascade_and_price_preservation),
        ("HTTP 404 Delisting: Ghost stock elimination on out_of_stock products", test_404_delisting_ghost_stock_elimination),
        ("HTTP 404 Delisting: Strict idempotency on already-depleted items", test_404_delisting_idempotency),

        # Category 3: Partial Variant Stock Shifts & Phantom Delta Elimination
        ("Variant Stock Shifts: 1 of 10 variant sell-out produces ZERO phantom events", test_partial_variant_stock_shift_zero_phantom_event),
        ("Variant Stock Shifts: 1 of 10 variant restock produces ZERO phantom events", test_partial_variant_restock_zero_phantom_event),
        ("Variant Stock Shifts: 1 -> 0 total depletion sets stock_changed=True", test_last_variant_sellout_legitimate_transition),
        ("Variant Stock Shifts: 0 -> 1 initial restock sets stock_changed=True", test_first_variant_restock_legitimate_transition),
        ("Variant Stock Shifts: Steady state unchanged inventory produces zero diffs", test_zero_inventory_shift_steady_state),

        # Category 4: Slug Apostrophe Stripping & Normalization
        ("Slug Normalization: Apostrophe and possessive stripping ('07, Women's, Men's, curly)", test_slug_normalization_apostrophe_stripping),
        ("Slug Normalization: Dynamic source_url generation without broken hyphens", test_delta_source_url_generation_from_slug),

        # Category 5: Rate Limiter & Circuit Breaker Robustness
        ("Rate Limiter Robustness: Permit acquisition, Akamai 403 & 429 circuit tripping", test_rate_limiter_handling_on_403_and_429),

        # Category 6: Whole-Rupee INR Math & Currency Harmony
        ("Currency Harmony: Whole-rupee INR rounding with zero fractional paise", test_whole_rupee_inr_math_on_price_shift),

        # Category 7: Multi-Tier Sizing & Token Collision Prevention
        ("Sizing Integrity: Multi-tier sizing classification and C/Y token preservation", test_sizing_category_classification_and_token_preservation)
    ]

    total = len(tests)
    passed = 0
    failed = 0
    failures = []

    t_suite_start = time.perf_counter()

    for name, fn in tests:
        ok, details = run_test_case(name, fn)
        if ok:
            passed += 1
        else:
            failed += 1
            failures.append((name, details))

    elapsed_suite = (time.perf_counter() - t_suite_start) * 1000

    print("\n" + "="*80)
    print("  ADVERSARIAL CHALLENGE SUMMARY REPORT  ")
    print("="*80)
    print(f"Total Tests Executed: {total}")
    print(f"Passed:              {passed}")
    print(f"Failed:              {failed}")
    print(f"Total Execution Time: {elapsed_suite:.1f}ms")
    print("="*80)

    if failed > 0:
        print("\n❌ VERDICT: REQUEST_CHANGES")
        print("Failures detected:")
        for fname, fdet in failures:
            print(f"  - {fname}: {fdet}")
        sys.exit(1)
    else:
        print("\n✅ VERDICT: APPROVE")
        print("All adversarial challenges satisfied the delta engine contract with 100% concordance.")
        sys.exit(0)


if __name__ == "__main__":
    main()
