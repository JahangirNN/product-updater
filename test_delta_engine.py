"""
Deep Test Suite for Stock & Price Delta Engine
Verifies configuration loading, timestamp-based scheduling, delta mutations,
Shopify event queueing, and live store connectivity.
Pure functions, zero classes (ADR 0005).
"""
import os
import sys
import json
import time
import datetime
import tempfile
import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from sync_catalog import load_delta_config, is_product_due, parse_iso_timestamp
from stores.jwpei.delta import check_price_and_stock, apply_delta_to_product
from storage.db import append_delta_event, append_delta_log


def test_config_loading():
    print("\n[TEST 1] Verifying Centralized Delta Configuration...")
    config = load_delta_config("config/delta_config.json")
    assert config is not None, "Config failed to load"
    assert config.get("check_interval_minutes") == 60, f"Expected 60m, got {config.get('check_interval_minutes')}"
    assert "jwpei" in config.get("store_configs", {}), "JW PEI store config missing"
    assert config["store_configs"]["jwpei"]["max_workers"] >= 1, "Invalid max_workers"
    assert "logging" in config, "Logging config block missing"
    assert config["logging"]["general_log"] == "freshner.log"
    assert config["logging"]["error_log"] == "errors.log"
    print("  ✅ PASS: config/delta_config.json parsed successfully with 60m default interval and logging setup.")


def test_interval_and_timestamp_filtering():
    print("\n[TEST 2] Verifying Product-Level Timestamp Interval Logic...")
    now_epoch = time.time()
    
    # Case A: Brand new product with no last_verified_at -> always due
    prod_new = {"id": "p_new"}
    due, _ = is_product_due(prod_new, interval_minutes=120)
    assert due is True, "Product without timestamp should be due"

    # Case B: Product verified 10 minutes ago, interval = 120 mins -> NOT due
    ts_10m_ago = datetime.datetime.fromtimestamp(now_epoch - 600, tz=datetime.timezone.utc).isoformat()
    prod_recent = {"id": "p_recent", "last_verified_at": ts_10m_ago}
    due, elapsed = is_product_due(prod_recent, interval_minutes=120)
    assert due is False, f"Product checked 10m ago should not be due for 120m check (elapsed={elapsed:.1f}m)"

    # Case C: Same product, but interval reduced to 2 minutes for testing -> DUE!
    due_short, _ = is_product_due(prod_recent, interval_minutes=2)
    assert due_short is True, "Product checked 10m ago should be due when interval=2m"

    # Case D: Force mode overrides any recent timestamp -> DUE!
    due_force, _ = is_product_due(prod_recent, interval_minutes=120, force=True)
    assert due_force is True, "Force mode should bypass timestamps"

    print("  ✅ PASS: Timestamp scheduling accurately filters due vs fresh products.")


def test_delta_mutation_and_shopify_queue():
    print("\n[TEST 3] Verifying Price Shift, Stock Depletion & Shopify Queue...")
    forex_rate = 94.843

    # Baseline product
    mock_product = {
        "id": "test_bag_001",
        "handle": "test-bag",
        "title": "Luxury Test Bag",
        "source_store": "jwpei",
        "source_price": 139.0,
        "current_price": 13183.0,
        "availability": "in_stock",
        "is_active": True,
        "variants": [
            {"sku": "TB-01", "is_available": True, "price_current": 13183.0}
        ]
    }

    # Simulation 1: Price drops from $139 to $119
    sim_delta_price = {
        "status": "success",
        "current_source_price": 119.0,
        "old_source_price": 139.0,
        "availability": "in_stock",
        "old_availability": "in_stock",
        "price_changed": True,
        "stock_changed": False,
        "is_active": True,
        "variants_delta": [{"sku": "TB-01", "available": True, "price_usd": 119.0}]
    }

    updated_prod, changed = apply_delta_to_product(mock_product.copy(), sim_delta_price, forex_rate)
    assert changed is True, "Delta should be detected"
    assert updated_prod["source_price"] == 119.0, f"Expected 119.0, got {updated_prod['source_price']}"
    assert updated_prod["current_price"] == round(119.0 * forex_rate), f"Expected INR {round(119.0 * forex_rate)}"
    assert updated_prod["shopify_sync_pending"] is True, "shopify_sync_pending must be True"
    assert "last_verified_at" in updated_prod, "last_verified_at must be updated"
    print("  ✅ PASS: Price shift accurately calculated in USD and converted to INR.")

    # Simulation 2: Stock depleted from in_stock to out_of_stock
    sim_delta_stock = {
        "status": "success",
        "current_source_price": 139.0,
        "old_source_price": 139.0,
        "availability": "out_of_stock",
        "old_availability": "in_stock",
        "price_changed": False,
        "stock_changed": True,
        "is_active": False,
        "variants_delta": [{"sku": "TB-01", "available": False, "price_usd": 139.0}]
    }

    updated_stock, stock_changed = apply_delta_to_product(mock_product.copy(), sim_delta_stock, forex_rate)
    assert stock_changed is True, "Stock change should be detected"
    assert updated_stock["availability"] == "out_of_stock", "Availability should be out_of_stock"
    assert updated_stock["is_active"] is False, "is_active should be False"
    assert updated_stock["shopify_sync_pending"] is True, "shopify_sync_pending must be True"
    print("  ✅ PASS: Stock depletion accurately flips availability and queues for Shopify.")

    # Simulation 3: Queue event creation
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_queue = os.path.join(tmp_dir, "test_delta_events.json")
        test_event = {
            "event_id": "evt_test_123",
            "store": "jwpei",
            "product_id": "test_bag_001",
            "handle": "test-bag",
            "price_changed": True,
            "old_source_price": 139.0,
            "new_source_price": 119.0,
            "stock_changed": False,
            "shopify_sync_pending": True
        }
        append_delta_event(test_event, queue_file=tmp_queue)
        assert os.path.exists(tmp_queue), "Queue file not written"
        with open(tmp_queue, "r", encoding="utf-8") as f:
            queue_data = json.load(f)
        assert len(queue_data) == 1, "Queue should have 1 event"
        assert queue_data[0]["event_id"] == "evt_test_123"
        print("  ✅ PASS: Event successfully written to Shopify delta queue.")


def test_live_jwpei_connectivity():
    print("\n[TEST 4] Verifying Live JW PEI Store Polling & Polite Pacing...")
    
    # Test In-Stock Product
    in_stock_product = {
        "handle": "thea-top-handle-bag-almond",
        "source_url": "https://www.jwpei.com/products/thea-top-handle-bag-almond",
        "source_price": 99.0,
        "availability": "in_stock"
    }

    t0 = time.time()
    res_in = check_price_and_stock(in_stock_product)
    dur_in = round((time.time() - t0) * 1000, 1)

    assert res_in["status"] == "success", f"Live check failed: {res_in}"
    assert res_in["current_source_price"] > 0, "Expected positive USD price"
    assert res_in["availability"] in ("in_stock", "out_of_stock")
    print(f"  ✅ PASS: In-Stock Product ({res_in['handle']}): ${res_in['current_source_price']} USD | {res_in['availability']} | latency: {dur_in}ms")

    # Test Known Sold-Out Product
    sold_out_product = {
        "handle": "thea-large-top-handle-bag-black",
        "source_url": "https://www.jwpei.com/products/thea-large-top-handle-bag-black",
        "source_price": 129.0,
        "availability": "out_of_stock"
    }

    t1 = time.time()
    res_out = check_price_and_stock(sold_out_product)
    dur_out = round((time.time() - t1) * 1000, 1)

    assert res_out["status"] == "success", f"Live check failed: {res_out}"
    assert res_out["availability"] == "out_of_stock", f"Expected out_of_stock for thea-large-top-handle-bag-black, got {res_out['availability']}"
    print(f"  ✅ PASS: Sold-Out Product ({res_out['handle']}): ${res_out['current_source_price']} USD | {res_out['availability']} | latency: {dur_out}ms")


def run_all_tests():
    print("=" * 68)
    print("DELTA ENGINE INTEGRATION & UNIT TEST SUITE")
    print("=" * 68)
    
    test_config_loading()
    test_interval_and_timestamp_filtering()
    test_delta_mutation_and_shopify_queue()
    test_live_jwpei_connectivity()

    print("\n" + "=" * 68)
    print("ALL TESTS PASSED WITH 100% SUCCESS")
    print("=" * 68)


if __name__ == "__main__":
    run_all_tests()
