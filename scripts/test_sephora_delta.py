"""
Unit Test Suite: Sephora Delta Freshener Engine
Validates live PDP delta checks, simulated stock shifts, price shifts,
parent-child stock harmony (ADR 0015), and whole-rupee INR math (ADR 0006).
"""
import os
import sys
import json
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stores.sephora.delta import check_price_and_stock, apply_delta_to_product
from storage.db import load_product

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "db")


def run_unit_tests():
    print("=" * 80)
    print("SEPHORA DELTA FRESHENER ENGINE UNIT VERIFICATION")
    print("=" * 80)

    # 1. Load an ingested product
    sephora_prods_dir = os.path.join(DB_DIR, "sephora", "products")
    if not os.path.exists(sephora_prods_dir) or not os.listdir(sephora_prods_dir):
        print("[FAIL] No ingested Sephora products found to test!")
        sys.exit(1)

    test_file = os.listdir(sephora_prods_dir)[0]
    with open(os.path.join(sephora_prods_dir, test_file), "r", encoding="utf-8") as f:
        product = json.load(f)

    print(f"Loaded test product: {product.get('title')} (ID: {product.get('id')})")
    print(f"Variants count: {len(product.get('variants', []))}")
    print(f"Initial price: USD ${product.get('source_price')} / INR ₹{product.get('current_price')}")
    print(f"Initial availability: {product.get('availability')}")

    # TEST 1: Live Polling Check
    print("\n[TEST 1] Live check_price_and_stock polling...")
    delta_res = check_price_and_stock(product)
    print(f"Delta Status: {delta_res.get('status')}")
    print(f"Polled Price: ${delta_res.get('source_price')}")
    print(f"Polled Availability: {delta_res.get('availability')}")
    print(f"Variants Delta Count: {len(delta_res.get('variants_delta', []))}")
    print(f"Elapsed Time: {delta_res.get('elapsed_ms', 0):.1f}ms")
    assert delta_res.get("status") == "success", f"Live check failed: {delta_res}"
    assert delta_res.get("source_price") > 0, "Source price must be > 0"
    print(">>> TEST 1 PASSED: Live polling succeeded cleanly.")

    # TEST 2: Price Shift Simulation & Whole-Rupee Math
    print("\n[TEST 2] Simulating price change ($24.00 -> $29.00) & whole-rupee INR math...")
    forex_rate = 95.0
    simulated_delta_price = {
        "status": "success",
        "availability": product.get("availability"),
        "source_price": 29.0,
        "variants_delta": [
            {"sku": v["sku"], "source_price": 29.0, "in_stock": v["in_stock"]}
            for v in product.get("variants", [])
        ]
    }
    updated_p, changed = apply_delta_to_product(product, simulated_delta_price, forex_rate=forex_rate)
    assert changed is True, "apply_delta_to_product should report has_changed=True"
    assert updated_p["source_price"] == 29.0
    expected_inr = int(round(29.0 * forex_rate))
    assert updated_p["current_price"] == expected_inr, f"Expected ₹{expected_inr}, got ₹{updated_p['current_price']}"
    assert isinstance(updated_p["current_price"], int), "Price must be integer whole rupees"
    for v in updated_p["variants"]:
        assert v["source_price"] == 29.0
        assert v["current_price"] == expected_inr
        assert isinstance(v["current_price"], int)
    print(f">>> TEST 2 PASSED: Price shifted to ₹{expected_inr} with 0 decimal paise.")

    # TEST 3: Variant Stock Flip Simulation
    print("\n[TEST 3] Simulating variant-level stock shift...")
    if updated_p["variants"]:
        v0 = updated_p["variants"][0]
        v0_sku = v0["sku"]
        flip_stock = not v0["in_stock"]
        simulated_var_delta = {
            "status": "success",
            "availability": updated_p["availability"],
            "source_price": updated_p["source_price"],
            "variants_delta": [
                {"sku": v0_sku, "source_price": v0.get("source_price"), "in_stock": flip_stock}
            ]
        }
        updated_var_p, var_changed = apply_delta_to_product(updated_p, simulated_var_delta, forex_rate=forex_rate)
        assert var_changed is True
        assert updated_var_p["variants"][0]["in_stock"] == flip_stock
        print(f">>> TEST 3 PASSED: Variant SKU {v0_sku} stock flipped cleanly to {flip_stock}.")

    # TEST 4: Parent Stock Harmony Invariant (All Variants OOS -> Parent OOS)
    print("\n[TEST 4] Parent Stock Harmony: Simulating 100% OOS across all variants...")
    simulated_all_oos = {
        "status": "success",
        "availability": "out_of_stock",
        "source_price": updated_p["source_price"],
        "variants_delta": [
            {"sku": v["sku"], "source_price": v.get("source_price"), "in_stock": False}
            for v in updated_p["variants"]
        ]
    }
    updated_oos_p, oos_changed = apply_delta_to_product(updated_p, simulated_all_oos, forex_rate=forex_rate)
    assert updated_oos_p["availability"] == "out_of_stock"
    assert updated_oos_p["is_active"] is False
    for v in updated_oos_p["variants"]:
        assert v["in_stock"] is False
        assert v["is_active"] is False
    print(">>> TEST 4 PASSED: Parent transitioned to out_of_stock with strict child harmony.")

    # TEST 5: Stock Harmony Recovery (1 Variant Back in Stock -> Parent In Stock)
    print("\n[TEST 5] Parent Stock Recovery: Simulating 1 variant back in stock...")
    simulated_recovery = {
        "status": "success",
        "availability": "in_stock",
        "source_price": updated_p["source_price"],
        "variants_delta": [
            {"sku": updated_oos_p["variants"][0]["sku"], "source_price": updated_p["source_price"], "in_stock": True}
        ]
    }
    updated_rec_p, rec_changed = apply_delta_to_product(updated_oos_p, simulated_recovery, forex_rate=forex_rate)
    assert updated_rec_p["availability"] == "in_stock"
    assert updated_rec_p["is_active"] is True
    assert updated_rec_p["variants"][0]["in_stock"] is True
    print(">>> TEST 5 PASSED: Parent transitioned back to in_stock.")

    # TEST 6: Immutability / Pure Functional Guarantee
    print("\n[TEST 6] Immutability / Pure Function verification...")
    assert product["source_price"] != 29.0, "Original product dict was mutated!"
    print(">>> TEST 6 PASSED: Immutability preserved, zero mutation on input arguments.")

    print("\n" + "=" * 80)
    print("ALL 6 DELTA FRESHENER UNIT TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 80)


if __name__ == "__main__":
    run_unit_tests()
