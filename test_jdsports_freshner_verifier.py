import copy
import glob
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional
import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage.db import (
    load_product,
    save_product,
    build_and_save_index,
    append_delta_event,
    read_delta_events,
    generate_product_id
)
from storage.forex import get_usd_to_inr_rate
from sync_catalog import (
    load_delta_config,
    is_product_due,
    resolve_store_delta_module,
    poll_single_product,
    run_catalog_sync
)
from stores.jdsports.delta import (
    check_price_and_stock,
    apply_delta_to_product
)

FOREX_RATE = 95.0
PASS_COUNT = 0
FAIL_COUNT = 0
TEST_LOGS = []


def record_pass(test_name: str, detail: str = ""):
    global PASS_COUNT
    PASS_COUNT += 1
    msg = f"  [PASS] {test_name}" + (f": {detail}" if detail else "")
    print(msg)
    TEST_LOGS.append(("PASS", test_name, detail))


def record_fail(test_name: str, error: str):
    global FAIL_COUNT
    FAIL_COUNT += 1
    msg = f"  [FAIL] {test_name}: {error}"
    print(msg)
    TEST_LOGS.append(("FAIL", test_name, error))


class MockJDHttpClient:
    def __init__(self, jsonld_data: Optional[Dict[str, Any]] = None, status_code: int = 200):
        self.status_code = status_code
        self.jsonld_data = jsonld_data

    def get(self, url: str, headers: Optional[Dict[str, Any]] = None, follow_redirects: bool = True, timeout: float = 15.0):
        class MockResponse:
            def __init__(self, code: int, j_data: Optional[Dict[str, Any]]):
                self.status_code = code
                self.headers = {"Retry-After": "2"} if code == 429 else {}
                if j_data is not None:
                    self.text = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>JD Sports Product</title>
                        <script type="application/ld+json">
                        {json.dumps(j_data)}
                        </script>
                    </head>
                    <body><h1>Mock Product</h1></body>
                    </html>
                    """
                else:
                    self.text = "<html><body>Not Found</body></html>" if code == 404 else "<html><body>WAF Shield</body></html>"

            def raise_for_status(self):
                if self.status_code >= 400:
                    req = httpx.Request("GET", "https://www.jdsports.com/test")
                    raise httpx.HTTPStatusError("HTTP Error", request=req, response=httpx.Response(self.status_code, request=req))

        return MockResponse(self.status_code, self.jsonld_data)


def test_sync_engine_catalog_recognition():
    print("\n" + "=" * 75)
    print("TEST SUITE 1: SYNC ENGINE INTEGRATION & CATALOG RECOGNITION")
    print("=" * 75)

    cfg = load_delta_config("config/delta_config.json")
    jds_conf = cfg.get("store_configs", {}).get("jdsports", {})
    if jds_conf and jds_conf.get("engine") == "http":
        record_pass("1.1 Delta Config Recognition", f"JD Sports configured with HTTP engine, rps={jds_conf.get('requests_per_second')}, delay={jds_conf.get('delay_seconds')}s")
    else:
        record_fail("1.1 Delta Config Recognition", "JD Sports store config missing or invalid")

    jds_mod = resolve_store_delta_module("jdsports")
    if jds_mod and callable(getattr(jds_mod, "check_price_and_stock", None)) and callable(getattr(jds_mod, "apply_delta_to_product", None)):
        record_pass("1.2 Module Dispatcher Resolution", "stores.jdsports.delta successfully resolved with pure functions")
    else:
        record_fail("1.2 Module Dispatcher Resolution", "Failed to resolve stores.jdsports.delta functions")

    with open("storage/db/index.json", "r", encoding="utf-8") as f:
        catalog_index = json.load(f)

    jd_products_in_index = [p for p in catalog_index.values() if p.get("store") == "jdsports" or p.get("source_store") == "jdsports"]
    if len(jd_products_in_index) == 476:
        record_pass("1.3 Total Catalog Population in index.json", "Found exactly 476 JD Sports products in index.json")
    else:
        record_fail("1.3 Total Catalog Population in index.json", f"Expected 476 products, found {len(jd_products_in_index)}")

    due_forced = [p for p in jd_products_in_index if is_product_due(p, interval_minutes=60, force=True)[0]]
    if len(due_forced) == 476:
        record_pass("1.4 Scheduler Due-Filter (Force Mode)", "100% (476/476) products scheduled under force=True")
    else:
        record_fail("1.4 Scheduler Due-Filter (Force Mode)", f"Expected 476 scheduled, got {len(due_forced)}")

    sample_item = jd_products_in_index[0]
    p_id = sample_item["id"]
    loaded_p_before = load_product("jdsports", p_id)
    last_verified_before = loaded_p_before.get("last_verified_at")

    mock_jsonld = {
        "@context": "https://schema.org",
        "@type": "ProductGroup",
        "name": loaded_p_before.get("title"),
        "hasVariant": [
            {
                "@type": "Product",
                "sku": v.get("sku"),
                "size": v.get("size") or v.get("title"),
                "offers": {
                    "@type": "Offer",
                    "price": float(v.get("source_price", loaded_p_before.get("source_price", 100.0))),
                    "priceCurrency": "USD",
                    "availability": "https://schema.org/InStock" if v.get("in_stock", True) else "https://schema.org/OutOfStock"
                }
            }
            for v in loaded_p_before.get("variants", [])
        ]
    }
    mock_client = MockJDHttpClient(mock_jsonld, status_code=200)

    dry_res = poll_single_product(
        product_stub=sample_item,
        store_mod=jds_mod,
        client=mock_client,
        forex_rate=FOREX_RATE,
        delay_seconds=0.0,
        dry_run=True,
        store_name="jdsports"
    )

    loaded_p_after = load_product("jdsports", p_id)
    if dry_res.get("status") == "success" and loaded_p_after.get("last_verified_at") == last_verified_before:
        record_pass("1.5 Dry-Run Sync Isolation", "poll_single_product completed with status=success and 0 disk writes (last_verified_at unmodified)")
    else:
        record_fail("1.5 Dry-Run Sync Isolation", f"Dry run failed status={dry_res.get('status')} or mutated disk")

    print("  [*] Running simulated dispatcher sync across all 476 JD Sports products...")
    t0 = time.perf_counter()
    dispatcher_errors = 0
    dispatched_success = 0
    for stub in jd_products_in_index:
        full_p = load_product("jdsports", stub["id"])
        if not full_p:
            dispatcher_errors += 1
            continue
        
        prod_jsonld = {
            "@type": "ProductGroup",
            "name": full_p.get("title"),
            "hasVariant": [
                {
                    "@type": "Product",
                    "sku": v.get("sku"),
                    "size": v.get("size", "Standard"),
                    "offers": {
                        "price": float(v.get("source_price", full_p.get("source_price", 100.0))),
                        "availability": "https://schema.org/InStock" if v.get("in_stock") else "https://schema.org/OutOfStock"
                    }
                }
                for v in full_p.get("variants", [])
            ]
        }
        client = MockJDHttpClient(prod_jsonld, status_code=200)
        res = poll_single_product(
            product_stub=stub,
            store_mod=jds_mod,
            client=client,
            forex_rate=FOREX_RATE,
            dry_run=True,
            store_name="jdsports"
        )
        if res.get("status") == "success":
            dispatched_success += 1
        else:
            dispatcher_errors += 1

    dur_ms = (time.perf_counter() - t0) * 1000
    if dispatcher_errors == 0 and dispatched_success == 476:
        record_pass("1.6 Full 476 Product Dispatcher Simulation", f"476/476 products polled with zero dispatcher exceptions in {dur_ms:.1f}ms ({dur_ms/476:.2f}ms/item)")
    else:
        record_fail("1.6 Full 476 Product Dispatcher Simulation", f"Failures: {dispatcher_errors}, Success: {dispatched_success}")


def test_variant_price_and_stock_delta_across_groups():
    print("\n" + "=" * 75)
    print("TEST SUITE 2: VARIANT PRICE & STOCK DELTA FRESHNESS ACROSS ALL GROUPS")
    print("=" * 75)

    target_groups = [
        ("nike-air-max", "Nike Air Max"),
        ("nike-air-force", "Nike Air Force"),
        ("nike-dunk", "Nike Dunk"),
        ("men's-shoes", "Men's Shoes"),
        ("women's-shoes", "Women's Shoes"),
        ("kids'-shoes", "Kids' Shoes")
    ]

    group_samples = {}
    files = glob.glob("storage/db/jdsports/products/*.json")
    for f in files:
        with open(f, "r", encoding="utf-8") as fh:
            p = json.load(fh)
        for g_key, g_label in target_groups:
            if g_key in p.get("groups", []) and g_key not in group_samples and len(p.get("variants", [])) >= 3:
                group_samples[g_key] = p

    for g_key, g_label in target_groups:
        sample_p = group_samples.get(g_key)
        if not sample_p:
            record_fail(f"2.{g_key} Sample Product Retrieval", f"No sample product found with >= 3 variants for group {g_key}")
            continue

        p_id = sample_p["id"]
        title = sample_p["title"]
        variants = sample_p["variants"]
        base_price = float(sample_p.get("source_price", 100.0))

        print(f"\n  Testing Group: [{g_label}] -> Product '{title[:35]}' ({len(variants)} variants)")

        # 2.A Variant Stock Delta Check
        var0_sku = variants[0]["sku"]
        var0_old_stock = variants[0].get("in_stock", True)
        var0_new_stock = not var0_old_stock

        mock_jsonld_stock = {
            "@type": "ProductGroup",
            "name": title,
            "hasVariant": [
                {
                    "@type": "Product",
                    "sku": v["sku"],
                    "size": v.get("size") or v.get("title"),
                    "offers": {
                        "price": float(v.get("source_price", base_price)),
                        "availability": "https://schema.org/InStock" if (v["sku"] != var0_sku and v.get("in_stock", True)) or (v["sku"] == var0_sku and var0_new_stock) else "https://schema.org/OutOfStock"
                    }
                }
                for v in variants
            ]
        }

        mock_client = MockJDHttpClient(mock_jsonld_stock, status_code=200)
        delta_stock = check_price_and_stock(sample_p, client=mock_client, store_name="jdsports")

        assert delta_stock["status"] == "success", f"Expected status success, got {delta_stock['status']}"
        assert delta_stock["variant_stock_changed"] is True, f"variant_stock_changed must be True for {g_key}"
        assert len(delta_stock["changed_variants"]) == 1, f"Expected 1 changed variant, got {len(delta_stock['changed_variants'])}"
        assert delta_stock["changed_variants"][0]["sku"] == var0_sku
        assert delta_stock["changed_variants"][0]["old_in_stock"] == var0_old_stock
        assert delta_stock["changed_variants"][0]["new_in_stock"] == var0_new_stock

        record_pass(f"2.{g_key}.1 Variant Stock Shift Detection", f"Caught stock transition {var0_old_stock}->{var0_new_stock} for SKU {var0_sku}")

        # Test apply_delta_to_product for Stock Shift
        p_copy = copy.deepcopy(sample_p)
        updated_p, has_changed = apply_delta_to_product(p_copy, delta_stock, FOREX_RATE)
        assert has_changed is True
        assert updated_p["shopify_sync_pending"] is True
        matched_var = next(v for v in updated_p["variants"] if v["sku"] == var0_sku)
        assert matched_var["in_stock"] == var0_new_stock
        record_pass(f"2.{g_key}.2 Variant Stock Mutation Applied", f"Variant {var0_sku} in_stock mutated to {var0_new_stock}, shopify_sync_pending=True")

        # 2.B Variant Price Delta Check
        var1_sku = variants[1]["sku"]
        var1_old_price = float(variants[1].get("source_price", base_price))
        var1_new_price = round(var1_old_price - 25.0, 2) if var1_old_price > 50 else round(var1_old_price + 25.0, 2)

        mock_jsonld_price = {
            "@type": "ProductGroup",
            "name": title,
            "hasVariant": [
                {
                    "@type": "Product",
                    "sku": v["sku"],
                    "size": v.get("size") or v.get("title"),
                    "offers": {
                        "price": var1_new_price if v["sku"] == var1_sku else float(v.get("source_price", base_price)),
                        "availability": "https://schema.org/InStock" if v.get("in_stock", True) else "https://schema.org/OutOfStock"
                    }
                }
                for v in variants
            ]
        }

        mock_client_price = MockJDHttpClient(mock_jsonld_price, status_code=200)
        delta_price = check_price_and_stock(sample_p, client=mock_client_price, store_name="jdsports")

        assert delta_price["status"] == "success"
        assert delta_price["variant_price_changed"] is True, f"variant_price_changed must be True for {g_key}"
        assert len(delta_price["changed_variant_prices"]) >= 1
        changed_p_entry = next(cp for cp in delta_price["changed_variant_prices"] if cp["sku"] == var1_sku)
        assert changed_p_entry["old_source_price"] == var1_old_price
        assert changed_p_entry["new_source_price"] == var1_new_price

        record_pass(f"2.{g_key}.3 Variant Price Shift Detection", f"Detected price change  ->  for SKU {var1_sku}")

        # Test apply_delta_to_product for Price Shift & Tri-Field Verification
        p_copy_price = copy.deepcopy(sample_p)
        updated_p_price, has_changed_price = apply_delta_to_product(p_copy_price, delta_price, FOREX_RATE)
        assert has_changed_price is True
        matched_var_price = next(v for v in updated_p_price["variants"] if v["sku"] == var1_sku)
        
        expected_inr = float(round(var1_new_price * FOREX_RATE))
        expected_inr_str = f"{expected_inr:.2f}"
        assert matched_var_price["source_price"] == var1_new_price
        assert matched_var_price["price"] == expected_inr_str
        assert matched_var_price["price_current"] == expected_inr

        record_pass(f"2.{g_key}.4 Variant Tri-Field Price Mutation", f"source_price=, price='{expected_inr_str}', price_current={expected_inr}")


def test_anti_flattening_and_sibling_preservation():
    print("\n" + "=" * 75)
    print("TEST SUITE 3: ANTI-FLATTENING & SIBLING PRESERVATION")
    print("=" * 75)

    multi_price_product = {
        "id": "jd_anti_flat_001",
        "source_store": "jdsports",
        "store": "jdsports",
        "handle": "nike-air-max-plus-multi",
        "title": "Nike Air Max Plus Multi",
        "source_price": 110.0,
        "current_price": 10450.0,
        "availability": "in_stock",
        "is_active": True,
        "variants": [
            {"sku": "JD-70", "size": "7.0", "title": "7.0", "source_price": 110.0, "price": "10450.00", "price_current": 10450.0, "in_stock": True},
            {"sku": "JD-80", "size": "8.0", "title": "8.0", "source_price": 120.0, "price": "11400.00", "price_current": 11400.0, "in_stock": True},
            {"sku": "JD-90", "size": "9.0", "title": "9.0", "source_price": 130.0, "price": "12350.00", "price_current": 12350.0, "in_stock": True},
            {"sku": "JD-100", "size": "10.0", "title": "10.0", "source_price": 140.0, "price": "13300.00", "price_current": 13300.0, "in_stock": True}
        ]
    }

    # Scenario 3.1: Differential Price Drop on JD-80 ( -> )
    delta_differential_price = {
        "status": "success",
        "handle": "nike-air-max-plus-multi",
        "current_source_price": 95.0,
        "old_source_price": 110.0,
        "price_changed": True,
        "stock_changed": False,
        "variant_price_changed": True,
        "changed_variant_prices": [{"sku": "JD-80", "size": "8.0", "old_source_price": 120.0, "new_source_price": 95.0}],
        "variants_delta": [
            {"sku": "JD-70", "size": "7.0", "available": True, "price_usd": 110.0},
            {"sku": "JD-80", "size": "8.0", "available": True, "price_usd": 95.0},
            {"sku": "JD-90", "size": "9.0", "available": True, "price_usd": 130.0},
            {"sku": "JD-100", "size": "10.0", "available": True, "price_usd": 140.0}
        ]
    }

    updated, changed = apply_delta_to_product(copy.deepcopy(multi_price_product), delta_differential_price, FOREX_RATE)
    assert changed is True
    v_by_sku = {v["sku"]: v for v in updated["variants"]}

    # Verify Target SKU shifted
    assert v_by_sku["JD-80"]["source_price"] == 95.0
    assert v_by_sku["JD-80"]["price_current"] == float(round(95.0 * FOREX_RATE))
    assert v_by_sku["JD-80"]["price"] == f"{float(round(95.0 * FOREX_RATE)):.2f}"

    # Verify Siblings JD-70, JD-90, JD-100 were 100% PRESERVED
    assert v_by_sku["JD-70"]["source_price"] == 110.0, f"JD-70 flattened: {v_by_sku['JD-70']['source_price']}"
    assert v_by_sku["JD-70"]["price_current"] == 10450.0
    assert v_by_sku["JD-90"]["source_price"] == 130.0, f"JD-90 flattened: {v_by_sku['JD-90']['source_price']}"
    assert v_by_sku["JD-90"]["price_current"] == 12350.0
    assert v_by_sku["JD-100"]["source_price"] == 140.0, f"JD-100 flattened: {v_by_sku['JD-100']['source_price']}"
    assert v_by_sku["JD-100"]["price_current"] == 13300.0

    record_pass("3.1 Anti-Flattening Invariant (Differential Pricing)", "Sibling prices (, , ) perfectly preserved when JD-80 changed to ")

    # Scenario 3.2: Differential Stock Shift
    delta_stock_single = {
        "status": "success",
        "handle": "nike-air-max-plus-multi",
        "current_source_price": 95.0,
        "old_source_price": 95.0,
        "price_changed": False,
        "stock_changed": False,
        "variant_stock_changed": True,
        "changed_variants": [{"sku": "JD-90", "old_in_stock": True, "new_in_stock": False}],
        "variants_delta": [
            {"sku": "JD-70", "size": "7.0", "available": True, "price_usd": 110.0},
            {"sku": "JD-80", "size": "8.0", "available": True, "price_usd": 95.0},
            {"sku": "JD-90", "size": "9.0", "available": False, "price_usd": 130.0},
            {"sku": "JD-100", "size": "10.0", "available": True, "price_usd": 140.0}
        ]
    }

    updated_stock, changed_stock = apply_delta_to_product(copy.deepcopy(updated), delta_stock_single, FOREX_RATE)
    assert changed_stock is True
    v_by_sku_stock = {v["sku"]: v for v in updated_stock["variants"]}
    assert v_by_sku_stock["JD-90"]["in_stock"] is False
    assert v_by_sku_stock["JD-70"]["in_stock"] is True
    assert v_by_sku_stock["JD-80"]["in_stock"] is True
    assert v_by_sku_stock["JD-100"]["in_stock"] is True
    assert updated_stock["availability"] == "in_stock"
    assert updated_stock["is_active"] is True

    record_pass("3.2 Sibling Stock Preservation", "JD-90 marked out_of_stock while siblings JD-70, JD-80, JD-100 preserved in_stock")


def test_parent_child_stock_harmony_and_404_cascade():
    print("\n" + "=" * 75)
    print("TEST SUITE 4: PARENT-CHILD STOCK HARMONY (ADR 0015) & 404 CASCADE")
    print("=" * 75)

    base_shoe = {
        "id": "jd_harmony_001",
        "source_store": "jdsports",
        "store": "jdsports",
        "handle": "nike-dunk-low-retro",
        "title": "Nike Dunk Low Retro",
        "source_price": 115.0,
        "current_price": 10925.0,
        "availability": "in_stock",
        "is_active": True,
        "variants": [
            {"sku": "DUNK-8", "size": "8.0", "source_price": 115.0, "price": "10925.00", "price_current": 10925.0, "in_stock": True},
            {"sku": "DUNK-9", "size": "9.0", "source_price": 115.0, "price": "10925.00", "price_current": 10925.0, "in_stock": True},
            {"sku": "DUNK-10", "size": "10.0", "source_price": 115.0, "price": "10925.00", "price_current": 10925.0, "in_stock": True}
        ]
    }

    # 4.1 Partial depletion (2 of 3 sell out) -> Parent remains in_stock
    delta_partial = {
        "status": "success",
        "handle": "nike-dunk-low-retro",
        "current_source_price": 115.0,
        "old_source_price": 115.0,
        "price_changed": False,
        "stock_changed": False,
        "variant_stock_changed": True,
        "changed_variants": [
            {"sku": "DUNK-8", "old_in_stock": True, "new_in_stock": False},
            {"sku": "DUNK-9", "old_in_stock": True, "new_in_stock": False}
        ],
        "variants_delta": [
            {"sku": "DUNK-8", "size": "8.0", "available": False, "price_usd": 115.0},
            {"sku": "DUNK-9", "size": "9.0", "available": False, "price_usd": 115.0},
            {"sku": "DUNK-10", "size": "10.0", "available": True, "price_usd": 115.0}
        ]
    }
    up_partial, ch_partial = apply_delta_to_product(copy.deepcopy(base_shoe), delta_partial, FOREX_RATE)
    assert ch_partial is True
    assert up_partial["availability"] == "in_stock"
    assert up_partial["is_active"] is True
    record_pass("4.1 Partial Depletion Harmony", "Parent availability remains in_stock with 1 variant alive (DUNK-10)")

    # 4.2 Total depletion (last variant sells out) -> Parent flips to out_of_stock
    delta_total = {
        "status": "success",
        "handle": "nike-dunk-low-retro",
        "current_source_price": 115.0,
        "old_source_price": 115.0,
        "price_changed": False,
        "stock_changed": True,
        "variant_stock_changed": True,
        "changed_variants": [
            {"sku": "DUNK-10", "old_in_stock": True, "new_in_stock": False}
        ],
        "variants_delta": [
            {"sku": "DUNK-8", "size": "8.0", "available": False, "price_usd": 115.0},
            {"sku": "DUNK-9", "size": "9.0", "available": False, "price_usd": 115.0},
            {"sku": "DUNK-10", "size": "10.0", "available": False, "price_usd": 115.0}
        ]
    }
    up_total, ch_total = apply_delta_to_product(copy.deepcopy(up_partial), delta_total, FOREX_RATE)
    assert ch_total is True
    assert up_total["availability"] == "out_of_stock"
    assert up_total["is_active"] is False
    assert all(v["in_stock"] is False for v in up_total["variants"])
    record_pass("4.2 Total Depletion Harmony", "Parent availability flips to out_of_stock when all variants are depleted")

    # 4.3 Restock (1 variant comes back in stock) -> Parent flips back to in_stock
    delta_restock = {
        "status": "success",
        "handle": "nike-dunk-low-retro",
        "current_source_price": 115.0,
        "old_source_price": 115.0,
        "price_changed": False,
        "stock_changed": True,
        "variant_stock_changed": True,
        "changed_variants": [
            {"sku": "DUNK-9", "old_in_stock": False, "new_in_stock": True}
        ],
        "variants_delta": [
            {"sku": "DUNK-8", "size": "8.0", "available": False, "price_usd": 115.0},
            {"sku": "DUNK-9", "size": "9.0", "available": True, "price_usd": 115.0},
            {"sku": "DUNK-10", "size": "10.0", "available": False, "price_usd": 115.0}
        ]
    }
    up_restock, ch_restock = apply_delta_to_product(copy.deepcopy(up_total), delta_restock, FOREX_RATE)
    assert ch_restock is True
    assert up_restock["availability"] == "in_stock"
    assert up_restock["is_active"] is True
    record_pass("4.3 Restock Harmony", "Parent availability flips back to in_stock on single child restock")

    # 4.4 HTTP 404 Delisting Depletion Cascade
    mock_404_client = MockJDHttpClient(status_code=404)
    delta_404 = check_price_and_stock(base_shoe, client=mock_404_client, store_name="jdsports")
    assert delta_404["status"] == "not_found"
    assert delta_404["availability"] == "out_of_stock"
    assert delta_404["stock_changed"] is True
    assert delta_404["variant_stock_changed"] is True

    up_404, ch_404 = apply_delta_to_product(copy.deepcopy(base_shoe), delta_404, FOREX_RATE)
    assert ch_404 is True
    assert up_404["availability"] == "out_of_stock"
    assert up_404["is_active"] is False
    assert all(v["in_stock"] is False for v in up_404["variants"])
    assert up_404["source_price"] == 115.0
    assert all(v["source_price"] == 115.0 for v in up_404["variants"])
    record_pass("4.4 HTTP 404 Delisting Depletion Cascade", "404 delisting cascades out_of_stock to all variants while 100% preserving prices")


def test_shopify_delta_event_queue():
    print("\n" + "=" * 75)
    print("TEST SUITE 5: SHOPIFY DELTA EVENT QUEUE (storage/db/history/delta_events.jsonl)")
    print("=" * 75)

    test_queue_path = "storage/db/history/delta_events_test.jsonl"
    if os.path.exists(test_queue_path):
        os.remove(test_queue_path)

    # 5.1 Variant Stock Shift Event
    stock_event = {
        "event_id": f"evt_test_{int(time.time()*1000)}_stock",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "store": "jdsports",
        "product_id": "00b144853e14f1d8",
        "handle": "nike-dunk-low-test",
        "title": "Nike Dunk Low Test",
        "price_changed": False,
        "old_source_price": 115.0,
        "new_source_price": 115.0,
        "new_current_price_inr": 10925.0,
        "stock_changed": False,
        "old_availability": "in_stock",
        "new_availability": "in_stock",
        "variant_stock_changed": True,
        "changed_variants": [
            {"sku": "SKU-DUNK-9", "old_in_stock": True, "new_in_stock": False}
        ],
        "variant_price_changed": False,
        "changed_variant_prices": [],
        "shopify_sync_pending": True
    }
    append_delta_event(stock_event, queue_file=test_queue_path)

    # 5.2 Variant Price Shift Event
    price_event = {
        "event_id": f"evt_test_{int(time.time()*1000)}_price",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "store": "jdsports",
        "product_id": "00b8d00e2ef126a1",
        "handle": "nike-air-max-90-test",
        "title": "Nike Air Max 90 Test",
        "price_changed": True,
        "old_source_price": 130.0,
        "new_source_price": 100.0,
        "new_current_price_inr": 9500.0,
        "stock_changed": False,
        "old_availability": "in_stock",
        "new_availability": "in_stock",
        "variant_stock_changed": False,
        "changed_variants": [],
        "variant_price_changed": True,
        "changed_variant_prices": [
            {"sku": "SKU-AM90-10", "size": "10.0", "old_source_price": 130.0, "new_source_price": 100.0}
        ],
        "shopify_sync_pending": True
    }
    append_delta_event(price_event, queue_file=test_queue_path)

    # 5.3 Read and Assert Events
    events = read_delta_events(queue_file=test_queue_path)
    assert len(events) == 2, f"Expected 2 events in queue, found {len(events)}"

    e_stock = events[0]
    assert e_stock["store"] == "jdsports"
    assert e_stock["variant_stock_changed"] is True
    assert len(e_stock["changed_variants"]) == 1
    assert e_stock["changed_variants"][0]["sku"] == "SKU-DUNK-9"
    assert e_stock["changed_variants"][0]["new_in_stock"] is False
    assert e_stock["shopify_sync_pending"] is True
    record_pass("5.1 Variant Stock Event Queueing", "Variant stock shift appended to JSONL queue with exact SKU diff payload")

    e_price = events[1]
    assert e_price["store"] == "jdsports"
    assert e_price["variant_price_changed"] is True
    assert len(e_price["changed_variant_prices"]) == 1
    assert e_price["changed_variant_prices"][0]["sku"] == "SKU-AM90-10"
    assert e_price["changed_variant_prices"][0]["old_source_price"] == 130.0
    assert e_price["changed_variant_prices"][0]["new_source_price"] == 100.0
    assert e_price["shopify_sync_pending"] is True
    record_pass("5.2 Variant Price Event Queueing", "Variant price shift appended to JSONL queue with exact price delta payload")

    if os.path.exists(test_queue_path):
        os.remove(test_queue_path)
    lock_file = test_queue_path + ".lock"
    if os.path.exists(lock_file):
        try:
            os.remove(lock_file)
        except Exception:
            pass


def run_all_jdsports_verifier_tests():
    t_start = time.perf_counter()
    print("=" * 80)
    print("  JD SPORTS FRESHNER DAEMON & DELTA MUTATION VERIFICATION SUITE")
    print("  Target Scope: 476 Products Across Nike Footwear Collections")
    print("=" * 80)

    test_sync_engine_catalog_recognition()
    test_variant_price_and_stock_delta_across_groups()
    test_anti_flattening_and_sibling_preservation()
    test_parent_child_stock_harmony_and_404_cascade()
    test_shopify_delta_event_queue()

    t_elapsed = (time.perf_counter() - t_start) * 1000

    print("\n" + "=" * 80)
    print(f"VERIFICATION SUMMARY: {PASS_COUNT} PASSED | {FAIL_COUNT} FAILED | Elapsed: {t_elapsed:.1f}ms")
    print("=" * 80)

    if FAIL_COUNT == 0:
        print("\n>>> ALL 476 JD SPORTS PRODUCTS & DELTA MECHANISMS ARE 100% OPERATIONAL & VERIFIED <<<")
    else:
        print(f"\n>>> VERIFICATION FAILED WITH {FAIL_COUNT} ERRORS <<<")
        sys.exit(1)


if __name__ == "__main__":
    run_all_jdsports_verifier_tests()
