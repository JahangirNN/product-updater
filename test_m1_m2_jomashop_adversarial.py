"""
Milestone M1/M2 Jomashop Ingestion Adversarial Empirical Verification Suite
Author: challenger_m1_m2_catalog

Verifies:
1. Product counts per brand: Versace (46), Tissot (157), Seiko (67), Citizen (119), Michael Kors (67) -> 456 total
2. File integrity: valid JSON, non-empty, unique IDs, unique SKUs
3. Whole-rupee INR pricing: assert price.is_integer(), zero fractional paise across products and variants
4. Case Diameter mapping:
   - Variant option_values contains option_name "Case Diameter" matching \d+(\.\d+)?\s*mm
   - Direct variant.get("size") check (adversarial exploration of key presence)
5. Accordion and technical specs in descriptionHtml across 100% of products
6. Master index synchronization in storage/db/index.json (456 entries, bidirectional 1:1 match)
7. Delta contract execution: check_price_and_stock and apply_delta_to_product
   - Success, price drop, stock flip, 404 delisting cascade, 429 rate limit, selective timestamping, stock harmony
8. Live PDP / GraphQL query test against Jomashop endpoint
"""
import copy
import glob
import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Tuple
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import httpx
from stores.jomashop.delta import check_price_and_stock, apply_delta_to_product, extract_url_key
from storage.forex import get_usd_to_inr_rate

PRODUCTS_DIR = os.path.join("storage", "db", "jomashop", "products")
INDEX_PATH = os.path.join("storage", "db", "index.json")

EXPECTED_BRAND_COUNTS = {
    "Versace": 46,
    "Tissot": 157,
    "Seiko": 67,
    "Citizen": 119,
    "Michael Kors": 67
}
TOTAL_EXPECTED = 456

results = []

def record_test(name: str, passed: bool, details: str):
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}: {details}")
    results.append({"name": name, "passed": passed, "details": details})


# ==============================================================================
# TEST 1: PRODUCT COUNTS AND BRAND DISTRIBUTION
# ==============================================================================
def test_product_counts_and_brands():
    files = glob.glob(os.path.join(PRODUCTS_DIR, "*.json"))
    total_files = len(files)
    if total_files != TOTAL_EXPECTED:
        record_test("Product File Count", False, f"Expected {TOTAL_EXPECTED} files, found {total_files}")
        return False, {}

    brand_counts = {}
    id_set = set()
    sku_set = set()
    corrupt_files = []

    for fpath in files:
        fname = os.path.basename(fpath)
        pid = fname[:-5]
        if os.path.getsize(fpath) == 0:
            corrupt_files.append((fpath, "Empty file (0 bytes)"))
            continue
        try:
            with open(fpath, "r", encoding="utf-8") as fp:
                data = json.load(fp)
        except Exception as e:
            corrupt_files.append((fpath, f"JSON parse error: {e}"))
            continue

        p_id = data.get("id")
        if p_id != pid:
            corrupt_files.append((fpath, f"ID mismatch: file {pid} vs data {p_id}"))
        if p_id in id_set:
            corrupt_files.append((fpath, f"Duplicate ID: {p_id}"))
        id_set.add(p_id)

        sku = data.get("source_sku") or data.get("sku")
        if sku:
            sku_set.add(sku)

        brand = data.get("vendor") or data.get("brand")
        brand_counts[brand] = brand_counts.get(brand, 0) + 1

    if corrupt_files:
        record_test("File & JSON Integrity", False, f"Found {len(corrupt_files)} corrupt files: {corrupt_files[:3]}")
        return False, {}
    else:
        record_test("File & JSON Integrity", True, f"All {total_files} files are valid JSON, non-empty, with matching IDs")

    brand_mismatch = False
    for brand, expected in EXPECTED_BRAND_COUNTS.items():
        actual = brand_counts.get(brand, 0)
        if actual != expected:
            brand_mismatch = True
            record_test(f"Brand Count - {brand}", False, f"Expected {expected}, got {actual}")
        else:
            record_test(f"Brand Count - {brand}", True, f"Exact match: {actual}/{expected}")

    return not brand_mismatch, brand_counts


# ==============================================================================
# TEST 2: WHOLE-RUPEE INR PRICING INVARIANT ACROSS ALL PRODUCTS & VARIANTS
# ==============================================================================
def test_whole_rupee_inr_pricing():
    files = glob.glob(os.path.join(PRODUCTS_DIR, "*.json"))
    failures = []
    total_variants = 0

    for fpath in files:
        with open(fpath, "r", encoding="utf-8") as fp:
            p = json.load(fp)

        pid = p.get("id")
        c_price = p.get("current_price")
        if c_price is None or not isinstance(c_price, (int, float)):
            failures.append((pid, f"Invalid current_price: {c_price}"))
            continue
        if not float(c_price).is_integer():
            failures.append((pid, f"Fractional current_price: {c_price}"))

        if c_price <= 0:
            failures.append((pid, f"Non-positive current_price: {c_price}"))

        variants = p.get("variants", [])
        if not variants:
            failures.append((pid, "Zero variants"))
            continue

        for idx, var in enumerate(variants):
            total_variants += 1
            v_price = var.get("price_current")
            if v_price is None or not isinstance(v_price, (int, float)):
                failures.append((pid, f"Variant {idx} invalid price_current: {v_price}"))
            elif not float(v_price).is_integer():
                failures.append((pid, f"Variant {idx} fractional price_current: {v_price}"))
            elif v_price <= 0:
                failures.append((pid, f"Variant {idx} non-positive price: {v_price}"))

            str_price = var.get("price")
            if str_price is None or not str(str_price).endswith(".00"):
                failures.append((pid, f"Variant {idx} string price does not end with .00: {str_price}"))

        # Check compare_at_price if present
        comp_price = p.get("compare_at_price")
        if comp_price is not None:
            if not isinstance(comp_price, (int, float)) or not float(comp_price).is_integer():
                failures.append((pid, f"Fractional compare_at_price: {comp_price}"))

    if failures:
        record_test("Whole-Rupee INR Pricing Invariant", False, f"Failures in {len(failures)} checks: {failures[:5]}")
        return False
    else:
        record_test("Whole-Rupee INR Pricing Invariant", True, f"100% verified across {len(files)} products and {total_variants} variants (0 fractional paise)")
        return True


# ==============================================================================
# TEST 3: CASE DIAMETER VARIANT SIZING
# ==============================================================================
def test_case_diameter_mapping():
    files = glob.glob(os.path.join(PRODUCTS_DIR, "*.json"))
    opt_failures = []
    direct_size_missing = 0
    case_pattern = re.compile(r'^\d+(\.\d+)?\s*mm$', re.IGNORECASE)

    for fpath in files:
        with open(fpath, "r", encoding="utf-8") as fp:
            p = json.load(fp)

        pid = p.get("id")
        variants = p.get("variants", [])
        for idx, var in enumerate(variants):
            # Check option_values representation
            opt_vals = var.get("option_values", [])
            cd_opts = [ov for ov in opt_vals if ov.get("option_name") == "Case Diameter"]
            if not cd_opts:
                opt_failures.append((pid, f"Variant {idx} missing 'Case Diameter' in option_values"))
            else:
                val_name = cd_opts[0].get("name", "")
                if not case_pattern.match(str(val_name).strip()):
                    opt_failures.append((pid, f"Variant {idx} Case Diameter value '{val_name}' invalid"))

            # Check direct variant['size'] key presence
            if not var.get("size"):
                direct_size_missing += 1

    if opt_failures:
        record_test("Case Diameter in option_values", False, f"Failures in {len(opt_failures)} variants: {opt_failures[:5]}")
        opt_ok = False
    else:
        record_test("Case Diameter in option_values", True, f"100% verified across {len(files)} products: 'Case Diameter' option present and matches \\d+(\\.\\d+)?\\s*mm")
        opt_ok = True

    # Note direct size key presence
    if direct_size_missing > 0:
        record_test("Direct variant['size'] Key", False, f"{direct_size_missing}/{len(files)} variants lack direct 'size' attribute (stored under option_values only)")
    else:
        record_test("Direct variant['size'] Key", True, f"All variants have direct 'size' key")

    return opt_ok


# ==============================================================================
# TEST 4: TECHNICAL SPECS & ACCORDION IN DESCRIPTION_HTML
# ==============================================================================
def test_specs_and_accordion_html():
    files = glob.glob(os.path.join(PRODUCTS_DIR, "*.json"))
    failures = []

    acc_re = re.compile(r'<details\s+class=[\"\']size-guide-accordion[\"\']', re.IGNORECASE)
    specs_div_re = re.compile(r'<div\s+class=[\"\']product-specifications[\"\']', re.IGNORECASE)
    specs_title_re = re.compile(r'Technical Specifications', re.IGNORECASE)
    summary_re = re.compile(r'<summary[^>]*>.*?Watch Sizing.*?Case Dimension Guide.*?</summary>', re.IGNORECASE | re.DOTALL)
    table_re = re.compile(r'<table[^>]*>', re.IGNORECASE)

    for fpath in files:
        with open(fpath, "r", encoding="utf-8") as fp:
            p = json.load(fp)

        pid = p.get("id")
        desc_html = p.get("descriptionHtml") or p.get("body_html") or ""
        if not desc_html:
            failures.append((pid, "Empty descriptionHtml"))
            continue

        if not acc_re.search(desc_html):
            failures.append((pid, "Missing '<details class=\"size-guide-accordion\"'"))
        if not specs_div_re.search(desc_html):
            failures.append((pid, "Missing '<div class=\"product-specifications\"'"))
        if not specs_title_re.search(desc_html):
            failures.append((pid, "Missing 'Technical Specifications' heading"))
        if not summary_re.search(desc_html):
            failures.append((pid, "Missing Watch Sizing summary in accordion"))
        if not table_re.search(desc_html):
            failures.append((pid, "Missing specs table"))

    if failures:
        record_test("Technical Specs & Accordion HTML", False, f"Failures in {len(failures)} checks: {failures[:5]}")
        return False
    else:
        record_test("Technical Specs & Accordion HTML", True, f"100% verified across all {len(files)} products: contains product-specifications div, technical specs table, and size-guide-accordion")
        return True


# ==============================================================================
# TEST 5: CITIZEN PRICE BOUNDARY [$100, $500]
# ==============================================================================
def test_citizen_price_boundary():
    files = glob.glob(os.path.join(PRODUCTS_DIR, "*.json"))
    citizen_count = 0
    failures = []

    for fpath in files:
        with open(fpath, "r", encoding="utf-8") as fp:
            p = json.load(fp)

        if (p.get("vendor") or p.get("brand")) == "Citizen":
            citizen_count += 1
            source_p = p.get("source_price")
            if source_p is None or source_p < 100.0 or source_p > 500.0:
                failures.append((p.get("id"), f"Citizen source_price ${source_p} outside [$100.00, $500.00]"))

    if citizen_count != 119:
        failures.append(("ALL", f"Expected 119 Citizen watches, found {citizen_count}"))

    if failures:
        record_test("Citizen Price Boundary [$100, $500]", False, f"Failures: {failures[:5]}")
        return False
    else:
        record_test("Citizen Price Boundary [$100, $500]", True, f"All {citizen_count} Citizen watches strictly within [$100.00, $500.00] USD")
        return True


# ==============================================================================
# TEST 6: MASTER INDEX SYNCHRONIZATION (storage/db/index.json)
# ==============================================================================
def test_master_index_sync():
    if not os.path.exists(INDEX_PATH):
        record_test("Master Index Sync", False, f"Index file not found: {INDEX_PATH}")
        return False

    with open(INDEX_PATH, "r", encoding="utf-8") as fp:
        index_data = json.load(fp)

    jomashop_in_index = {k: v for k, v in index_data.items() if v.get("store") == "jomashop"}
    idx_count = len(jomashop_in_index)

    if idx_count != TOTAL_EXPECTED:
        record_test("Master Index Count", False, f"Expected {TOTAL_EXPECTED} Jomashop entries in index.json, got {idx_count}")
        return False
    else:
        record_test("Master Index Count", True, f"Exactly {idx_count} Jomashop entries found in master index")

    files = glob.glob(os.path.join(PRODUCTS_DIR, "*.json"))
    mismatches = []
    file_ids = set()

    for fpath in files:
        pid = os.path.basename(fpath)[:-5]
        file_ids.add(pid)
        if pid not in jomashop_in_index:
            mismatches.append((pid, "Product file exists on disk but missing in index.json"))
            continue

        with open(fpath, "r", encoding="utf-8") as fp:
            prod = json.load(fp)

        idx_entry = jomashop_in_index[pid]

        # Verify exact field alignments with storage/db.py build_and_save_index schema
        if idx_entry.get("current_price_inr") != prod.get("current_price"):
            mismatches.append((pid, f"current_price_inr mismatch: disk {prod.get('current_price')} vs index {idx_entry.get('current_price_inr')}"))
        if idx_entry.get("source_price_usd") != prod.get("source_price"):
            mismatches.append((pid, f"source_price_usd mismatch: disk {prod.get('source_price')} vs index {idx_entry.get('source_price_usd')}"))
        if idx_entry.get("availability") != prod.get("availability"):
            mismatches.append((pid, f"availability mismatch: disk {prod.get('availability')} vs index {idx_entry.get('availability')}"))
        if idx_entry.get("sku") != prod.get("source_sku"):
            mismatches.append((pid, f"sku mismatch: disk {prod.get('source_sku')} vs index {idx_entry.get('sku')}"))
        if idx_entry.get("handle") != prod.get("handle"):
            mismatches.append((pid, f"handle mismatch: disk {prod.get('handle')} vs index {idx_entry.get('handle')}"))
        expected_fpath = f"jomashop/products/{pid}.json"
        if idx_entry.get("file_path") != expected_fpath:
            mismatches.append((pid, f"file_path mismatch: expected {expected_fpath} vs index {idx_entry.get('file_path')}"))

    for k in jomashop_in_index.keys():
        if k not in file_ids:
            mismatches.append((k, "Index entry exists but missing product file on disk"))

    if mismatches:
        record_test("Master Index Parity", False, f"Found {len(mismatches)} discrepancies: {mismatches[:5]}")
        return False
    else:
        record_test("Master Index Parity", True, f"100% 1-to-1 parity between all 456 disk files and master index entries (price, sku, handle, path, availability)")
        return True


# ==============================================================================
# TEST 7: UNIVERSAL DELTA CONTRACT STRESS TESTS (stores/jomashop/delta.py)
# ==============================================================================
def test_delta_contract_suite():
    forex = 88.0

    base_product = {
        "id": "test_joma_001",
        "handle": "versace-chrono-v-watch",
        "url_key": "versace-chrono-v-watch",
        "source_sku": "VER-12345",
        "title": "Versace Chrono Watch",
        "vendor": "Versace",
        "source_price": 450.0,
        "current_price": 39600.0,
        "source_compare_at_price": 995.0,
        "compare_at_price": 87560.0,
        "availability": "in_stock",
        "is_active": True,
        "variants": [
            {
                "id": "v1",
                "sku": "VER-12345",
                "title": "42 mm",
                "size": "42 mm",
                "option_name": "Case Diameter",
                "source_price": 450.0,
                "price": "39600.00",
                "price_current": 39600.0,
                "in_stock": True,
                "is_available": True
            }
        ],
        "created_at": "2026-09-22T00:00:00Z",
        "updated_at": "2026-09-22T00:00:00Z"
    }

    # SUBTEST 7.1: check_price_and_stock on 200 IN_STOCK with price drop
    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {
        "data": {
            "products": {
                "items": [
                    {
                        "id": "999",
                        "sku": "VER-12345",
                        "url_key": "versace-chrono-v-watch",
                        "stock_status": "IN_STOCK",
                        "price_range": {
                            "minimum_price": {
                                "regular_price": {"value": 400.0, "currency": "USD"},
                                "final_price": {"value": 400.0, "currency": "USD"},
                                "msrp_price": {"value": 995.0, "currency": "USD"}
                            }
                        }
                    }
                ]
            }
        }
    }

    mock_client = MagicMock()
    mock_client.post.return_value = mock_resp_200

    delta_res = check_price_and_stock(base_product, client=mock_client)
    assert delta_res["status"] == "success"
    assert delta_res["is_active"] is True
    assert delta_res["availability"] == "in_stock"
    assert delta_res["current_source_price"] == 400.0
    assert delta_res["price_changed"] is True
    assert delta_res["stock_changed"] is False
    assert delta_res["variant_price_changed"] is True

    # Apply delta
    p_copy = copy.deepcopy(base_product)
    updated_p, has_changed = apply_delta_to_product(p_copy, delta_res, forex_rate=forex)
    assert has_changed is True
    assert updated_p["source_price"] == 400.0
    assert updated_p["current_price"] == 35200.0
    assert updated_p["current_price"].is_integer()
    assert updated_p["variants"][0]["source_price"] == 400.0
    assert updated_p["variants"][0]["price_current"] == 35200.0
    assert updated_p["variants"][0]["price_current"].is_integer()
    assert updated_p["variants"][0]["price"] == "35200.00"
    assert "last_verified_at" in updated_p
    record_test("Delta Contract: Price Drop & Variant Sync", True, "Successfully detected price drop and updated whole-rupee INR")

    # SUBTEST 7.2: check_price_and_stock on 200 OUT_OF_STOCK
    mock_resp_oos = MagicMock()
    mock_resp_oos.status_code = 200
    mock_resp_oos.json.return_value = {
        "data": {
            "products": {
                "items": [
                    {
                        "id": "999",
                        "sku": "VER-12345",
                        "url_key": "versace-chrono-v-watch",
                        "stock_status": "OUT_OF_STOCK",
                        "price_range": {
                            "minimum_price": {
                                "regular_price": {"value": 450.0, "currency": "USD"},
                                "final_price": {"value": 450.0, "currency": "USD"},
                                "msrp_price": {"value": 995.0, "currency": "USD"}
                            }
                        }
                    }
                ]
            }
        }
    }
    mock_client.post.return_value = mock_resp_oos
    delta_res_oos = check_price_and_stock(base_product, client=mock_client)
    assert delta_res_oos["status"] == "success"
    assert delta_res_oos["availability"] == "out_of_stock"
    assert delta_res_oos["stock_changed"] is True
    assert delta_res_oos["variant_stock_changed"] is True

    p_copy = copy.deepcopy(base_product)
    updated_p, has_changed = apply_delta_to_product(p_copy, delta_res_oos, forex_rate=forex)
    assert has_changed is True
    assert updated_p["availability"] == "out_of_stock"
    assert updated_p["is_active"] is False
    assert updated_p["variants"][0]["in_stock"] is False
    record_test("Delta Contract: Stock Flip to Out of Stock", True, "Stock flipped to out_of_stock and child variant marked in_stock: False")

    # SUBTEST 7.3: HTTP 404 Delisting stock cascade & price preservation (ADR 0015)
    mock_resp_404 = MagicMock()
    mock_resp_404.status_code = 404
    mock_client.post.return_value = mock_resp_404
    delta_res_404 = check_price_and_stock(base_product, client=mock_client)
    assert delta_res_404["status"] == "not_found"
    assert delta_res_404["availability"] == "out_of_stock"
    assert delta_res_404["old_source_price"] == 450.0
    assert delta_res_404["current_source_price"] == 450.0

    p_copy = copy.deepcopy(base_product)
    updated_p, has_changed = apply_delta_to_product(p_copy, delta_res_404, forex_rate=forex)
    assert has_changed is True
    assert updated_p["availability"] == "out_of_stock"
    assert updated_p["is_active"] is False
    assert updated_p["source_price"] == 450.0
    assert updated_p["current_price"] == 39600.0
    assert all(v["in_stock"] is False for v in updated_p["variants"])
    assert "last_verified_at" in updated_p
    record_test("Delta Contract: 404 Delisting Stock Cascade", True, "Depleted child variants, set out_of_stock, preserved price history, stamped last_verified_at")

    # SUBTEST 7.4: Selective timestamp stamping on rate limit and error (ADR 0008)
    p_copy = copy.deepcopy(base_product)
    p_copy.pop("last_verified_at", None)

    rate_limit_delta = {
        "status": "rate_limited",
        "availability": "in_stock",
        "current_source_price": 450.0
    }
    updated_p, has_changed = apply_delta_to_product(p_copy, rate_limit_delta, forex_rate=forex)
    assert has_changed is False
    assert "last_verified_at" not in updated_p

    error_delta = {
        "status": "error",
        "error": "Connection reset by peer"
    }
    updated_p, has_changed = apply_delta_to_product(p_copy, error_delta, forex_rate=forex)
    assert has_changed is False
    assert "last_verified_at" not in updated_p
    record_test("Delta Contract: Selective Timestamp Stamping", True, "Verified last_verified_at is NEVER stamped on rate_limited or error")

    # SUBTEST 7.5: Whole-rupee assertion on exotic fractional forex rates
    exotic_rates = [83.4567, 89.1234, 91.9999, 85.0001]
    for rate in exotic_rates:
        p_copy = copy.deepcopy(base_product)
        delta_res = {
            "status": "success",
            "price_changed": True,
            "current_source_price": 199.99
        }
        updated_p, _ = apply_delta_to_product(p_copy, delta_res, forex_rate=rate)
        assert updated_p["current_price"].is_integer()
    record_test("Delta Contract: Exotic Forex Whole-Rupee Rounding", True, "Guaranteed 0 fractional paise across exotic float forex rates")

    # SUBTEST 7.6: Stock Harmony invariant (ADR 0015)
    p_copy = copy.deepcopy(base_product)
    p_copy["variants"] = [
        {"id": "v1", "sku": "S1", "in_stock": True},
        {"id": "v2", "sku": "S2", "in_stock": False}
    ]
    p_copy["availability"] = "out_of_stock"
    delta_dummy = {"status": "success", "variants_delta": []}
    updated_p, has_ch = apply_delta_to_product(p_copy, delta_dummy, forex_rate=forex)
    assert updated_p["availability"] == "in_stock"
    assert updated_p["is_active"] is True

    p_copy["variants"] = [
        {"id": "v1", "sku": "S1", "in_stock": False},
        {"id": "v2", "sku": "S2", "in_stock": False}
    ]
    p_copy["availability"] = "in_stock"
    updated_p, has_ch = apply_delta_to_product(p_copy, delta_dummy, forex_rate=forex)
    assert updated_p["availability"] == "out_of_stock"
    assert updated_p["is_active"] is False
    record_test("Delta Contract: Parent-Variant Stock Harmony", True, "Parent availability matches variant in_stock logic 100%")

    return True


# ==============================================================================
# TEST 8: LIVE GRAPHQL ENDPOINT HEALTH CHECK
# ==============================================================================
def test_live_jomashop_graphql():
    files = glob.glob(os.path.join(PRODUCTS_DIR, "*.json"))
    if not files:
        record_test("Live GraphQL Endpoint", False, "No product files to test")
        return False

    sample_fpath = files[0]
    with open(sample_fpath, "r", encoding="utf-8") as fp:
        sample_prod = json.load(fp)

    url_key = extract_url_key(sample_prod)
    print(f"Sampling live product url_key: {url_key}")

    try:
        delta_res = check_price_and_stock(sample_prod)
        status = delta_res.get("status")
        price = delta_res.get("current_source_price")
        avail = delta_res.get("availability")
        elapsed = delta_res.get("elapsed_ms")

        if status in ("success", "not_found"):
            record_test("Live GraphQL Query", True, f"Status: {status}, Price: ${price}, Availability: {avail}, Latency: {elapsed}ms")
            return True
        elif status == "rate_limited":
            record_test("Live GraphQL Query", True, f"Rate limited handled gracefully (Status: {status})")
            return True
        else:
            record_test("Live GraphQL Query", False, f"Unexpected status: {status}, error: {delta_res.get('error')}")
            return False
    except Exception as e:
        record_test("Live GraphQL Query", False, f"Exception during live call: {e}")
        return False


def main():
    print("=" * 80)
    print("STARTING ADVERSARIAL VERIFICATION SUITE: JOMASHOP M1/M2 INGESTION")
    print("=" * 80)

    t0 = time.time()
    test_product_counts_and_brands()
    test_whole_rupee_inr_pricing()
    test_case_diameter_mapping()
    test_specs_and_accordion_html()
    test_citizen_price_boundary()
    test_master_index_sync()
    test_delta_contract_suite()
    test_live_jomashop_graphql()
    elapsed = time.time() - t0

    print("=" * 80)
    print(f"VERIFICATION COMPLETE IN {elapsed:.2f}s")
    print("=" * 80)

    total_tests = len(results)
    passed_tests = sum(1 for r in results if r["passed"])
    failed_tests = total_tests - passed_tests
    print(f"SUMMARY: {passed_tests}/{total_tests} tests passed ({failed_tests} failed/flagged).")

    # If all critical tests pass except the architectural finding regarding direct variant['size'] key:
    critical_passes = all(r["passed"] for r in results if r["name"] != "Direct variant['size'] Key")

    if critical_passes:
        print("VERDICT: CONFIRM (with 1 architectural caveat on direct variant['size'] vs option_values)")
        sys.exit(0)
    else:
        print("VERDICT: CHALLENGE")
        sys.exit(1)


if __name__ == "__main__":
    main()
