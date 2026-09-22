"""
Deep Test Suite for Stock & Price Delta Engine
Verifies configuration loading, timestamp-based scheduling, delta mutations,
Shopify event queueing, rate limiting, circuit breaker, browser fingerprinting,
and live store connectivity.
Pure functions, zero classes (ADR 0005, ADR 0010).
"""
import os
import sys
import json
import time
import datetime
import tempfile
import threading
import copy
from typing import List
import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from sync_catalog import (
    load_delta_config,
    is_product_due,
    parse_iso_timestamp,
    poll_single_product,
    run_catalog_sync
)
from stores.jwpei.delta import check_price_and_stock as jwpei_check, apply_delta_to_product as jwpei_apply
from stores._template.delta import check_price_and_stock as template_check, apply_delta_to_product as template_apply
from stores.footlocker.delta import check_price_and_stock as fl_check, apply_delta_to_product as fl_apply
from stores.nordstrom.delta import check_price_and_stock as nordstrom_check, apply_delta_to_product as nordstrom_apply
from stores.coach.delta import check_price_and_stock as coach_check, apply_delta_to_product as coach_apply, matches_coach_size
from stores.michaelkors.delta import check_price_and_stock as mk_check, apply_delta_to_product as mk_apply
from stores.jdsports.delta import check_price_and_stock as jdsports_check, apply_delta_to_product as jdsports_apply
from stores.jomashop.delta import check_price_and_stock as jomashop_check, apply_delta_to_product as jomashop_apply
from storage.db import append_delta_event, append_delta_log, read_delta_events
from storage.rate_limiter import (
    configure_store_rate_limits,
    get_store_rate_limits,
    parse_retry_after,
    trip_circuit_breaker,
    is_circuit_open,
    get_cooldown_remaining,
    acquire_permit,
    create_store_limiter,
    reset_rate_limiter
)
from storage.network import (
    get_browser_headers,
    create_http_client,
    create_connection_limits,
    CHROME_133_USER_AGENT
)


def test_config_loading():
    print("\n[TEST 1] Verifying Centralized Multi-Store Delta Configuration...")
    config = load_delta_config("config/delta_config.json")
    assert config is not None, "Config failed to load"
    assert config.get("check_interval_minutes") == 60, f"Expected 60m, got {config.get('check_interval_minutes')}"
    assert config.get("default_max_workers") == 2, f"Expected default_max_workers=2, got {config.get('default_max_workers')}"
    assert config.get("default_requests_per_second") == 2.0, f"Expected default_requests_per_second=2.0, got {config.get('default_requests_per_second')}"
    assert config.get("default_delay_seconds") == 0.5, f"Expected default_delay_seconds=0.5, got {config.get('default_delay_seconds')}"
    assert config.get("default_timeout_seconds") == 8.0, f"Expected default_timeout_seconds=8.0, got {config.get('default_timeout_seconds')}"

    assert "jwpei" in config.get("store_configs", {}), "JW PEI store config missing"
    jwpei_cfg = config["store_configs"]["jwpei"]
    assert jwpei_cfg["max_workers"] >= 1, "Invalid max_workers"
    assert jwpei_cfg["requests_per_second"] == 2.0, f"Expected jwpei requests_per_second=2.0, got {jwpei_cfg.get('requests_per_second')}"
    assert jwpei_cfg["delay_seconds"] == 0.5, f"Expected jwpei delay_seconds=0.5, got {jwpei_cfg.get('delay_seconds')}"

    assert "logging" in config, "Logging config block missing"
    assert config["logging"]["general_log"] == "freshner.log"
    assert config["logging"]["error_log"] == "errors.log"
    print("  ✅ PASS: config/delta_config.json parsed successfully with store-agnostic defaults and jwpei profile.")


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

    updated_prod, changed = jwpei_apply(mock_product.copy(), sim_delta_price, forex_rate)
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

    updated_stock, stock_changed = jwpei_apply(mock_product.copy(), sim_delta_stock, forex_rate)
    assert stock_changed is True, "Stock change should be detected"
    assert updated_stock["availability"] == "out_of_stock", "Availability should be out_of_stock"
    assert updated_stock["is_active"] is False, "is_active should be False"
    assert updated_stock["shopify_sync_pending"] is True, "shopify_sync_pending must be True"
    print("  ✅ PASS: Stock depletion accurately flips availability and queues for Shopify.")

    # Simulation 3: Queue event creation
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_queue = os.path.join(tmp_dir, "test_delta_events.jsonl")
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
        queue_data = read_delta_events(tmp_queue)
        assert len(queue_data) == 1, "Queue should have 1 event"
        assert queue_data[0]["event_id"] == "evt_test_123"
        print("  ✅ PASS: Event successfully written to Shopify delta queue.")


def test_rate_limiter_and_circuit_breaker():
    print("\n[TEST 4] Verifying Pure Functional Rate Limiter & Circuit Breaker...")
    reset_rate_limiter()

    # 1. Test configuration & retrieval
    configure_store_rate_limits("test_store", requests_per_second=10.0, delay_seconds=0.05)
    rps, delay = get_store_rate_limits("test_store")
    assert rps == 10.0, f"Expected rps=10.0, got {rps}"
    assert delay == 0.05, f"Expected delay=0.05, got {delay}"

    # Default fallback
    def_rps, def_delay = get_store_rate_limits("unknown_store")
    assert def_rps == 2.0
    assert def_delay == 0.5

    # 2. Test Retry-After parsing
    assert parse_retry_after("12") == 12.0
    assert parse_retry_after("4.5") == 4.5
    assert parse_retry_after(None, default_cooldown=15.0) == 15.0
    assert parse_retry_after("", default_cooldown=15.0) == 15.0
    assert parse_retry_after("invalid", default_cooldown=20.0) == 20.0

    # 3. Test Circuit Breaker Tripping & Cooldown State
    assert not is_circuit_open("test_store")
    assert get_cooldown_remaining("test_store") == 0.0

    trip_circuit_breaker("test_store", cooldown_seconds=0.2)
    assert is_circuit_open("test_store")
    assert get_cooldown_remaining("test_store") > 0.0

    # Sleep past cooldown
    time.sleep(0.25)
    assert not is_circuit_open("test_store")
    assert get_cooldown_remaining("test_store") == 0.0

    # 4. Test Sibling Threads Cooldown & Anti-Thundering-Herd Pacing
    # Configure fast test store (10 rps -> 0.1s interval)
    configure_store_rate_limits("concurrent_store", requests_per_second=10.0, delay_seconds=0.1)
    results: List[float] = []

    def worker():
        acquire_permit("concurrent_store")
        results.append(time.time())

    # Trip breaker for 0.3s
    trip_circuit_breaker("concurrent_store", cooldown_seconds=0.3)
    t_start = time.time()

    threads = [threading.Thread(target=worker) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All threads must have executed strictly AFTER the 0.3s cooldown
    for exec_ts in results:
        assert (exec_ts - t_start) >= 0.28, f"Thread executed prematurely during cooldown: {exec_ts - t_start:.3f}s"

    # Threads must be spaced by rate limit (at least ~0.04s spacing accounting for OS scheduler jitter)
    results.sort()
    diff1 = results[1] - results[0]
    diff2 = results[2] - results[1]
    assert diff1 >= 0.04, f"Thread 2 followed Thread 1 too quickly (thundering herd): {diff1:.3f}s"
    assert diff2 >= 0.04, f"Thread 3 followed Thread 2 too quickly (thundering herd): {diff2:.3f}s"

    reset_rate_limiter()
    print("  ✅ PASS: Pure functional rate limiter enforces pacing, circuit breaker pauses siblings, and prevents thundering herds.")


def test_browser_fingerprinting():
    print("\n[TEST 5] Verifying Chrome 133 Fingerprinting & Network Pooling...")
    headers = get_browser_headers()

    assert "Chrome/133" in headers.get("User-Agent", ""), "User-Agent does not identify as Chrome 133"
    assert "133" in headers.get("Sec-Ch-Ua", ""), "Sec-Ch-Ua missing Chrome 133 mark"
    assert headers.get("Sec-Ch-Ua-Mobile") == "?0", "Sec-Ch-Ua-Mobile mismatch"
    assert headers.get("Sec-Ch-Ua-Platform") == '"Windows"', "Sec-Ch-Ua-Platform mismatch"
    assert headers.get("Sec-Fetch-Dest") == "empty", "Sec-Fetch-Dest mismatch"
    assert headers.get("Sec-Fetch-Mode") == "cors", "Sec-Fetch-Mode mismatch"

    limits = create_connection_limits(max_keepalive_connections=5, max_connections=10)
    assert limits.max_keepalive_connections == 5, f"Expected 5 keepalive, got {limits.max_keepalive_connections}"
    assert limits.max_connections == 10, f"Expected 10 max connections, got {limits.max_connections}"

    with create_http_client(timeout_seconds=5.0) as client:
        assert client.headers.get("User-Agent") == CHROME_133_USER_AGENT
        assert client.headers.get("Sec-Ch-Ua-Mobile") == "?0"
        assert client.headers.get("Sec-Fetch-Mode") == "cors"
        assert client.headers.get("Sec-Fetch-Dest") == "empty"

    print("  ✅ PASS: Modern Chrome 133 Client Hints and connection pooling limits verified.")


def test_resilience_and_selective_timestamping():
    print("\n[TEST 6] Verifying 404 Preservation & Selective Timestamp Stamping...")
    forex_rate = 94.843

    original_product = {
        "id": "p_resilience_01",
        "handle": "resilient-tote",
        "source_price": 89.0,
        "current_price": 8441.0,
        "availability": "in_stock",
        "last_verified_at": "2026-09-01T00:00:00Z"
    }

    # Case 1: Rate Limited (429 retries exhausted)
    res_rate_limited = {
        "status": "rate_limited",
        "handle": "resilient-tote",
        "old_source_price": 89.0,
        "current_source_price": 89.0,
        "old_availability": "in_stock",
        "availability": "in_stock",
        "error": "Rate limit retries exhausted (HTTP 429)"
    }
    prod_after_429, changed_429 = jwpei_apply(original_product.copy(), res_rate_limited, forex_rate)
    assert not changed_429, "Rate limited check must not report changes"
    assert prod_after_429["last_verified_at"] == "2026-09-01T00:00:00Z", "Rate limited check MUST NOT stamp last_verified_at"

    # Case 2: Network / 5xx Error
    res_error = {
        "status": "error",
        "handle": "resilient-tote",
        "old_source_price": 89.0,
        "current_source_price": 89.0,
        "error": "Connection timeout"
    }
    prod_after_err, changed_err = jwpei_apply(original_product.copy(), res_error, forex_rate)
    assert not changed_err, "Error check must not report changes"
    assert prod_after_err["last_verified_at"] == "2026-09-01T00:00:00Z", "Error check MUST NOT stamp last_verified_at"

    # Case 3: 404 Delisting -> preserves fields and STAMPS timestamp
    res_404 = {
        "status": "not_found",
        "handle": "resilient-tote",
        "availability": "out_of_stock",
        "old_availability": "in_stock",
        "current_source_price": 89.0,
        "old_source_price": 89.0,
        "is_active": False,
        "price_changed": False,
        "stock_changed": True,
        "message": "Product delisted (HTTP 404)"
    }
    assert res_404["old_availability"] == "in_stock"
    assert res_404["current_source_price"] == 89.0
    assert res_404["old_source_price"] == 89.0

    prod_after_404, changed_404 = jwpei_apply(original_product.copy(), res_404, forex_rate)
    assert changed_404 is True, "404 delisting must trigger stock change"
    assert prod_after_404["availability"] == "out_of_stock"
    assert prod_after_404["is_active"] is False
    assert prod_after_404["last_verified_at"] != "2026-09-01T00:00:00Z", "404 delisting MUST stamp last_verified_at"

    # Verify identical contract on stores/_template/delta.py
    tpl_after_429, _ = template_apply(original_product.copy(), res_rate_limited, forex_rate)
    assert tpl_after_429["last_verified_at"] == "2026-09-01T00:00:00Z"
    tpl_after_404, _ = template_apply(original_product.copy(), res_404, forex_rate)
    assert tpl_after_404["last_verified_at"] != "2026-09-01T00:00:00Z"

    print("  ✅ PASS: Rate limited and error statuses never stamp last_verified_at; 404 preserves prices and stamps timestamp.")


def test_live_jwpei_connectivity():
    print("\n[TEST 7] Verifying Live JW PEI Store Polling & Polite Pacing...")

    # Test In-Stock Product
    in_stock_product = {
        "handle": "thea-top-handle-bag-almond",
        "source_url": "https://www.jwpei.com/products/thea-top-handle-bag-almond",
        "source_price": 99.0,
        "availability": "in_stock"
    }

    t0 = time.time()
    res_in = jwpei_check(in_stock_product)
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
    res_out = jwpei_check(sold_out_product)
    dur_out = round((time.time() - t1) * 1000, 1)

    assert res_out["status"] == "success", f"Live check failed: {res_out}"
    assert res_out["availability"] in ("in_stock", "out_of_stock"), f"Invalid availability: {res_out['availability']}"
    assert res_out["current_source_price"] > 0, "Price should be positive"
    print(f"  ✅ PASS: Live Product Polled ({res_out['handle']}): ${res_out['current_source_price']} USD | {res_out['availability']} | latency: {dur_out}ms")


def test_multi_store_isolation_and_429_circuit_breaking():
    print("\n[TEST 8] Verifying Multi-Store Isolation & HTTP 429 Circuit Tripping...")
    reset_rate_limiter()

    # 1. Multi-Store Isolation:
    # Store A and Store B configured with 10 rps (0.1s interval)
    configure_store_rate_limits("store_a", requests_per_second=10.0, delay_seconds=0.1)
    configure_store_rate_limits("store_b", requests_per_second=10.0, delay_seconds=0.1)

    # Trip breaker ONLY on store_a for 0.4s
    trip_circuit_breaker("store_a", cooldown_seconds=0.4)
    assert is_circuit_open("store_a") is True
    assert is_circuit_open("store_b") is False, "store_b circuit breaker must NOT be tripped when store_a trips"

    # Store B must acquire permit immediately without waiting for store_a cooldown
    t_start_b = time.time()
    waited_b = acquire_permit("store_b")
    dur_b = time.time() - t_start_b
    assert dur_b < 0.15, f"store_b should execute immediately without waiting for store_a cooldown (took {dur_b:.3f}s)"

    # Store A threads must respect cooldown
    t_start_a = time.time()
    waited_a = acquire_permit("store_a")
    dur_a = time.time() - t_start_a
    assert dur_a >= 0.35, f"store_a must pause for circuit cooldown (took {dur_a:.3f}s)"

    # 2. Test create_store_limiter functional handle
    limiter_b = create_store_limiter("store_b")
    assert limiter_b["store"] == "store_b"
    assert callable(limiter_b["acquire_permit"])
    assert callable(limiter_b["trip_circuit_breaker"])
    assert limiter_b["is_circuit_open"]() is False
    limiter_b["trip_circuit_breaker"](0.2)
    assert limiter_b["is_circuit_open"]() is True
    assert is_circuit_open("store_b") is True

    # 3. Test HTTP 429 handling inside delta check with mock client
    class Mock429Response:
        status_code = 429
        headers = {"Retry-After": "1"}

    class Mock429Client:
        def get(self, url):
            return Mock429Response()

    # Product with mock client that always returns 429
    prod_429 = {"handle": "mock-tote", "source_url": "https://www.jwpei.com/products/mock-tote", "source_price": 50.0}
    limiter_mock = create_store_limiter("mock_429_store")
    res_429 = jwpei_check(prod_429, client=Mock429Client(), store_name="mock_429_store", rate_limiter=limiter_mock)

    assert res_429["status"] == "rate_limited", f"Expected rate_limited status, got {res_429['status']}"
    assert is_circuit_open("mock_429_store") is True, "Circuit breaker should be open after 429 exhaustion"

    reset_rate_limiter()
    print("  ✅ PASS: Store isolation verified (Store A tripped != Store B blocked), store limiter handles confirmed, and 429 exhaustion handled cleanly.")


def test_dispatcher_resilience_and_contracts():
    print("\n[TEST 9] Verifying Dispatcher Resilience, Signature Introspection & Result Contracts...")

    # 1. Test run_catalog_sync result contract when 0 products due
    empty_result = run_catalog_sync(interval_override=999999.0, dry_run=True)
    assert "duration_seconds" in empty_result, "run_catalog_sync missing duration_seconds in empty return dict"
    assert "scanned" in empty_result
    assert "errors" in empty_result
    assert "rate_limited" in empty_result

    # 2. Test missing product file branch
    test_missing_stub = {"id": "nonexistent_prod_999", "handle": "missing-item", "source_store": "jwpei"}
    res_missing = poll_single_product(
        product_stub=test_missing_stub,
        store_mod=jwpei_check,
        client=httpx.Client(),
        forex_rate=90.0,
        delay_seconds=0.1,
        dry_run=True,
        store_name="jwpei"
    )
    assert res_missing["status"] == "error"
    assert "not found on disk" in res_missing["error"]

    # 3. Test poll_single_product with a store module that raises an internal TypeError
    # Simulates store module with a bug inside check_price_and_stock
    class BuggyStoreModule:
        @staticmethod
        def check_price_and_stock(product, client=None, store_name="buggy", rate_limiter=None):
            # Internal TypeError (e.g. data bug)
            raise TypeError("Simulated internal TypeError in store scraper")

        @staticmethod
        def apply_delta_to_product(product, delta_result, forex_rate):
            return product, False

    test_prod_stub = {"id": "006291ad60a33773", "handle": "hana-large-tote-bag-pink", "source_store": "jwpei"}
    mock_client = httpx.Client()
    res_buggy = poll_single_product(
        product_stub=test_prod_stub,
        store_mod=BuggyStoreModule,
        client=mock_client,
        forex_rate=90.0,
        delay_seconds=0.1,
        dry_run=True,
        store_name="jwpei"
    )
    mock_client.close()

    # Must return a structured error dictionary without bubbling or crashing
    assert res_buggy["status"] == "error"
    assert "Simulated internal TypeError" in res_buggy["error"]
    assert res_buggy["id"] == "006291ad60a33773"

    # 4. Test poll_single_product with legacy module signature (no client, no rate_limiter)
    class LegacyStoreModule:
        @staticmethod
        def check_price_and_stock(product):
            return {"status": "success", "handle": "hana-large-tote-bag-pink", "current_source_price": 50.0, "old_source_price": 50.0, "availability": "in_stock"}

        @staticmethod
        def apply_delta_to_product(product, delta_result, forex_rate):
            return product, False

    test_legacy_stub = {"id": "006291ad60a33773", "handle": "hana-large-tote-bag-pink", "source_store": "jwpei"}
    mock_client2 = httpx.Client()
    res_legacy = poll_single_product(
        product_stub=test_legacy_stub,
        store_mod=LegacyStoreModule,
        client=mock_client2,
        forex_rate=90.0,
        delay_seconds=0.1,
        dry_run=True,
        store_name="jwpei"
    )
    mock_client2.close()
    assert res_legacy["status"] == "success"
    assert res_legacy["handle"] == "hana-large-tote-bag-pink"

    print("  ✅ PASS: Dispatcher safely isolates internal store exceptions and introspects legacy and modern store module signatures.")


def test_footlocker_delta_cascade_and_selective_timestamping():
    print("\n[TEST 10] Verifying Foot Locker Delta Cascade, 404 Depletion & Selective Timestamping...")
    forex_rate = 95.957

    product_fl = {
        "id": "fl_vomero_01",
        "handle": "nike-vomero-5-mens-v1358003",
        "source_store": "footlocker",
        "source_sku": "V1358003",
        "source_price": 160.0,
        "current_price": 15353.0,
        "availability": "in_stock",
        "is_active": True,
        "last_verified_at": "2026-09-01T00:00:00Z",
        "variants": [
            {"sku": "V1358003-8", "in_stock": True, "source_price": 160.0, "price": "15353.00", "title": "US 8 / UK 7"},
            {"sku": "V1358003-9", "in_stock": True, "source_price": 160.0, "price": "15353.00", "title": "US 9 / UK 8"},
            {"sku": "V1358003-10", "in_stock": True, "source_price": 160.0, "price": "15353.00", "title": "US 10 / UK 9"}
        ]
    }

    # Case 1: Partial variant sellout (size 8 and 9 sell out, size 10 still available)
    # Parent availability stays "in_stock", but variants must update and has_changed must be True!
    delta_partial = {
        "status": "success",
        "handle": product_fl["handle"],
        "current_source_price": 160.0,
        "old_source_price": 160.0,
        "availability": "in_stock",
        "old_availability": "in_stock",
        "price_changed": False,
        "stock_changed": False,
        "variant_stock_changed": True,
        "variants_delta": [
            {"sku": "V1358003-8", "size": "8", "available": False, "price_usd": 160.0},
            {"sku": "V1358003-9", "size": "9", "available": False, "price_usd": 160.0},
            {"sku": "V1358003-10", "size": "10", "available": True, "price_usd": 160.0}
        ]
    }
    updated_p1, changed_p1 = fl_apply(copy.deepcopy(product_fl), delta_partial, forex_rate)
    assert changed_p1 is True, "Partial variant sellout must report has_changed = True"
    assert updated_p1["availability"] == "in_stock", "Parent should remain in_stock because size 10 is available"
    assert updated_p1["is_active"] is True
    v_map1 = {v["sku"]: v["in_stock"] for v in updated_p1["variants"]}
    assert v_map1["V1358003-8"] is False, "Size 8 must be out_of_stock"
    assert v_map1["V1358003-9"] is False, "Size 9 must be out_of_stock"
    assert v_map1["V1358003-10"] is True, "Size 10 must remain in_stock"
    assert updated_p1["last_verified_at"] != "2026-09-01T00:00:00Z"

    # Case 2: Complete Depletion via 404 delisting (ADR 0015 cascade)
    delta_404 = {
        "status": "not_found",
        "handle": product_fl["handle"],
        "availability": "out_of_stock",
        "old_availability": "in_stock",
        "current_source_price": 160.0,
        "old_source_price": 160.0,
        "is_active": False,
        "price_changed": False,
        "stock_changed": True,
        "variants_delta": []
    }
    updated_404, changed_404 = fl_apply(copy.deepcopy(product_fl), delta_404, forex_rate)
    assert changed_404 is True, "404 delisting must trigger change"
    assert updated_404["availability"] == "out_of_stock", "404 must set availability to out_of_stock"
    assert updated_404["is_active"] is False, "404 must set is_active to False"
    # CRITICAL INVARIANT: all child variants must be cascaded to in_stock = False!
    for v in updated_404["variants"]:
        assert v["in_stock"] is False, f"Variant {v['sku']} must be cascaded to False on 404 delisting"
    assert updated_404["last_verified_at"] != "2026-09-01T00:00:00Z", "404 must stamp last_verified_at"

    # Case 3: Rate limited (429 retries exhausted) - MUST NOT mutate and MUST NOT stamp timestamp
    delta_429 = {
        "status": "rate_limited",
        "handle": product_fl["handle"],
        "availability": "in_stock",
        "old_availability": "in_stock",
        "current_source_price": 160.0,
        "old_source_price": 160.0,
        "error": "Rate limit retries exhausted"
    }
    updated_429, changed_429 = fl_apply(copy.deepcopy(product_fl), delta_429, forex_rate)
    assert changed_429 is False, "Rate limited check must report changed = False"
    assert updated_429["last_verified_at"] == "2026-09-01T00:00:00Z", "Rate limited check MUST NOT stamp last_verified_at"

    print("  ✅ PASS: Foot Locker partial variant inventory shifts update cleanly, 404 delistings cascade depletion, and rate limits maintain immutability.")


def test_nordstrom_multicolorway_delta_and_price_range_sync():
    print("\n[TEST 11] Verifying Nordstrom Multi-Colorway Delta Mutation & Clearance Leak Prevention...")
    forex_rate = 95.957

    # Initial product: 2 colorways (Black: $140, Coral Sale: $99.90)
    # Lowest price is Coral $99.90.
    product_nord = {
        "id": "nord_cloud_5",
        "handle": "on-cloud-5-sneaker",
        "title": "On Cloud 5 Running Sneaker",
        "source_store": "nordstrom",
        "source_price": 99.90,
        "current_price": 9586.0,
        "availability": "in_stock",
        "is_active": True,
        "price_range_usd": {"min": 99.90, "max": 140.00},
        "price_range_inr": {"min": 9586.0, "max": 13434.0},
        "last_verified_at": "2026-09-01T00:00:00Z",
        "variants": [
            {"sku": "NORD-100-BLK-8", "in_stock": True, "source_price": 140.0, "price": "13434.00", "title": "Black / 8"},
            {"sku": "NORD-100-BLK-9", "in_stock": True, "source_price": 140.0, "price": "13434.00", "title": "Black / 9"},
            {"sku": "NORD-100-CRL-8", "in_stock": True, "source_price": 99.90, "price": "9586.00", "title": "Coral / 8"},
            {"sku": "NORD-100-CRL-9", "in_stock": True, "source_price": 99.90, "price": "9586.00", "title": "Coral / 9"}
        ]
    }

    # Scenario A: The sale colorway (Coral) completely sells out!
    # Black remains in stock at $140.00.
    # CRITICAL INVARIANT: The parent source_price MUST shift to $140.0, preventing clearance price leak!
    delta_coral_soldout = {
        "status": "success",
        "handle": product_nord["handle"],
        "availability": "in_stock",
        "old_availability": "in_stock",
        "price_changed": False,
        "stock_changed": False,
        "variants_delta": [
            {"sku": "NORD-100-BLK-8", "available": True, "price_usd": 140.0},
            {"sku": "NORD-100-BLK-9", "available": True, "price_usd": 140.0},
            {"sku": "NORD-100-CRL-8", "available": False, "price_usd": 99.90},
            {"sku": "NORD-100-CRL-9", "available": False, "price_usd": 99.90}
        ]
    }

    updated_a, changed_a = nordstrom_apply(copy.deepcopy(product_nord), delta_coral_soldout, forex_rate)
    assert changed_a is True, "Variant stock changes must trigger has_changed = True"
    assert updated_a["availability"] == "in_stock", "Product should remain in stock since Black is available"
    # Clearance price leak prevention check:
    assert updated_a["source_price"] == 140.0, f"Parent source_price must update to lowest IN-STOCK variant ($140.0), got {updated_a['source_price']}"
    assert updated_a["current_price"] == float(round(140.0 * forex_rate)), "Parent INR price must derive from in-stock price"
    assert updated_a["current_price"] % 1 == 0, "INR price must be whole-rupee (no decimal paise)"
    assert updated_a["price_range_usd"]["min"] == 99.90
    assert updated_a["price_range_usd"]["max"] == 140.0
    assert updated_a["price_range_inr"]["min"] == float(round(99.90 * forex_rate))
    assert updated_a["price_range_inr"]["max"] == float(round(140.0 * forex_rate))
    assert updated_a["last_verified_at"] != "2026-09-01T00:00:00Z"
    assert updated_a["shopify_sync_pending"] is True

    # Scenario B: HTTP 404 delisting cascades depletion to ALL variants (ADR 0015)
    delta_404 = {
        "status": "not_found",
        "handle": product_nord["handle"],
        "availability": "out_of_stock",
        "old_availability": "in_stock",
        "is_active": False,
        "price_changed": False,
        "stock_changed": True,
        "variants_delta": []
    }
    updated_404, changed_404 = nordstrom_apply(copy.deepcopy(product_nord), delta_404, forex_rate)
    assert changed_404 is True, "404 delisting must trigger change"
    assert updated_404["availability"] == "out_of_stock"
    assert updated_404["is_active"] is False
    for v in updated_404["variants"]:
        assert v["in_stock"] is False, f"Variant {v['sku']} must cascade to in_stock=False on 404"
    assert updated_404["last_verified_at"] != "2026-09-01T00:00:00Z"

    # Scenario C: Blocked/Error/429 status preserves immutability and never stamps last_verified_at
    delta_blocked = {
        "status": "blocked",
        "handle": product_nord["handle"],
        "availability": "in_stock",
        "old_availability": "in_stock",
        "current_source_price": 99.90,
        "old_source_price": 99.90,
        "error": "Kasada challenge unresolved"
    }
    updated_blk, changed_blk = nordstrom_apply(copy.deepcopy(product_nord), delta_blocked, forex_rate)
    assert changed_blk is False
    assert updated_blk["last_verified_at"] == "2026-09-01T00:00:00Z", "Blocked solver MUST NOT stamp last_verified_at"

    print("  ✅ PASS: Nordstrom multi-colorway variant inventory shifts update cleanly, clearance price leaks are prevented, and 404 delistings cascade depletion.")


def test_coach_multivariant_delta_and_scene7_integrity():
    print("\n[TEST 12] Verifying Coach Multi-Variant Delta Mutation, Scene7 Integrity & Depletion Cascade...")
    forex_rate = 95.957

    scene7_img1 = "https://images.coach.com/is/image/Coach/ch782_b4bk_a0?fmt=jpeg&wid=1034&qlt=75"
    scene7_img2 = "https://images.coach.com/is/image/Coach/ch782_b4ha_a0?fmt=jpeg&wid=1034&qlt=75"

    product_coach = {
        "id": "coach_tabby_26",
        "handle": "tabby-shoulder-bag-26",
        "title": "Tabby Shoulder Bag 26",
        "source_store": "coach",
        "source_sku": "CH782",
        "source_price": 395.0,
        "current_price": 37903.0,
        "availability": "in_stock",
        "is_active": True,
        "images": [scene7_img1, scene7_img2],
        "last_verified_at": "2026-09-01T00:00:00Z",
        "variants": [
            {
                "sku": "CH782 B4/BK",
                "in_stock": True,
                "source_price": 450.0,
                "price": "43181.00",
                "title": "Black",
                "image": scene7_img1
            },
            {
                "sku": "CH782 B4/HA",
                "in_stock": True,
                "source_price": 395.0,
                "price": "37903.00",
                "title": "Chalk",
                "image": scene7_img2
            }
        ]
    }

    # Scenario A: Chalk sells out and Black price increases to $475
    delta_chalk_out = {
        "status": "success",
        "handle": product_coach["handle"],
        "current_source_price": 475.0,
        "old_source_price": 395.0,
        "availability": "in_stock",
        "old_availability": "in_stock",
        "price_changed": True,
        "stock_changed": False,
        "variants_delta": [
            {"sku": "CH782 B4/BK", "available": True, "price_usd": 475.0},
            {"sku": "CH782 B4/HA", "available": False, "price_usd": 395.0}
        ]
    }

    updated_c, changed_c = coach_apply(copy.deepcopy(product_coach), delta_chalk_out, forex_rate)
    assert changed_c is True, "Price shift and stock mutation must trigger changed = True"
    assert updated_c["availability"] == "in_stock"
    assert updated_c["source_price"] == 475.0
    assert updated_c["current_price"] == float(round(475.0 * forex_rate))
    assert updated_c["current_price"] % 1 == 0, "INR price must be whole-rupee without paise"

    v_map = {v["sku"]: v for v in updated_c["variants"]}
    assert v_map["CH782 B4/BK"]["in_stock"] is True
    assert v_map["CH782 B4/BK"]["source_price"] == 475.0
    assert v_map["CH782 B4/HA"]["in_stock"] is False

    # CRITICAL: Verify Scene7 image URLs were never corrupted or dropped during delta mutation
    assert updated_c["images"][0] == scene7_img1
    assert updated_c["images"][1] == scene7_img2
    assert v_map["CH782 B4/BK"]["image"] == scene7_img1
    assert v_map["CH782 B4/HA"]["image"] == scene7_img2
    assert updated_c["last_verified_at"] != "2026-09-01T00:00:00Z"

    # Scenario B: 404 delisting cascades depletion (ADR 0015)
    delta_404 = {
        "status": "not_found",
        "handle": product_coach["handle"],
        "availability": "out_of_stock",
        "old_availability": "in_stock",
        "current_source_price": 475.0,
        "old_source_price": 475.0,
        "is_active": False,
        "price_changed": False,
        "stock_changed": True,
        "variants_delta": []
    }
    updated_404, changed_404 = coach_apply(copy.deepcopy(product_coach), delta_404, forex_rate)
    assert changed_404 is True
    assert updated_404["availability"] == "out_of_stock"
    assert updated_404["is_active"] is False
    for v in updated_404["variants"]:
        assert v["in_stock"] is False, f"Coach variant {v['sku']} must be cascaded to in_stock=False on 404"

    # Scenario C: HTTP 429 rate limit maintains strict immutability
    delta_429 = {
        "status": "rate_limited",
        "handle": product_coach["handle"],
        "availability": "in_stock",
        "old_availability": "in_stock",
        "error": "Rate limit retries exhausted"
    }
    updated_429, changed_429 = coach_apply(copy.deepcopy(product_coach), delta_429, forex_rate)
    assert changed_429 is False
    assert updated_429["last_verified_at"] == "2026-09-01T00:00:00Z"

    print("  ✅ PASS: Coach multi-variant stock & price updates mutate cleanly, Scene7 image URLs maintain integrity, and depletion cascades safely.")


def test_jdsports_multitier_delta_and_depletion_cascade():
    print("\n[TEST 13] Verifying JD Sports Multi-Tier Sizing Delta Mutation, 404 Cascade & Rate Limit Resilience...")
    forex_rate = 95.989567

    product_jds = {
        "id": "jds_air_max_90",
        "handle": "mens-nike-air-max-90-casual-shoes-ib7680-001",
        "title": "Men's Nike Air Max 90 Casual Shoes - Black/Buff Gold/Anthracite",
        "source_store": "jdsports",
        "source_sku": "IB7680-001",
        "source_price": 120.0,
        "current_price": 11519.0,
        "availability": "in_stock",
        "is_active": True,
        "sizing_category": "Adult",
        "last_verified_at": "2026-09-01T00:00:00Z",
        "variants": [
            {"sku": "IB7680-001-8.0", "in_stock": True, "source_price": 120.0, "price": "11519.00", "title": "US 8.0 / UK 7 - Black/Buff Gold/Anthracite"},
            {"sku": "IB7680-001-9.0", "in_stock": True, "source_price": 120.0, "price": "11519.00", "title": "US 9.0 / UK 8 - Black/Buff Gold/Anthracite"},
            {"sku": "IB7680-001-10.0", "in_stock": True, "source_price": 120.0, "price": "11519.00", "title": "US 10.0 / UK 9 - Black/Buff Gold/Anthracite"}
        ]
    }

    # Scenario A: Partial variant inventory update + price increase ($120 -> $130)
    delta_success = {
        "status": "success",
        "handle": product_jds["handle"],
        "current_source_price": 130.0,
        "old_source_price": 120.0,
        "availability": "in_stock",
        "old_availability": "in_stock",
        "price_changed": True,
        "stock_changed": False,
        "variant_stock_changed": True,
        "variants_delta": [
            {"sku": "IB7680-001-8.0", "size": "8.0", "available": False, "price_usd": 130.0},
            {"sku": "IB7680-001-9.0", "size": "9.0", "available": True, "price_usd": 130.0},
            {"sku": "IB7680-001-10.0", "size": "10.0", "available": False, "price_usd": 130.0}
        ]
    }
    updated_a, changed_a = jdsports_apply(copy.deepcopy(product_jds), delta_success, forex_rate)
    assert changed_a is True, "Price and variant stock changes must return has_changed = True"
    assert updated_a["source_price"] == 130.0
    assert updated_a["current_price"] == float(round(130.0 * forex_rate))
    assert updated_a["current_price"] % 1 == 0, "INR price must be whole-rupee (no fractional paise)"
    assert updated_a["availability"] == "in_stock", "Parent must remain in_stock because size 9.0 is available"
    assert updated_a["is_active"] is True
    v_map = {v["sku"]: v["in_stock"] for v in updated_a["variants"]}
    assert v_map["IB7680-001-8.0"] is False
    assert v_map["IB7680-001-9.0"] is True
    assert v_map["IB7680-001-10.0"] is False
    assert updated_a["last_verified_at"] != "2026-09-01T00:00:00Z", "Success must advance last_verified_at"
    assert updated_a["shopify_sync_pending"] is True

    # Scenario B: 404 delisting cascades depletion to all child variants (ADR 0015)
    delta_404 = {
        "status": "not_found",
        "handle": product_jds["handle"],
        "availability": "out_of_stock",
        "old_availability": "in_stock",
        "current_source_price": 120.0,
        "old_source_price": 120.0,
        "is_active": False,
        "price_changed": False,
        "stock_changed": True,
        "variant_stock_changed": True,
        "variants_delta": []
    }
    updated_404, changed_404 = jdsports_apply(copy.deepcopy(product_jds), delta_404, forex_rate)
    assert changed_404 is True
    assert updated_404["availability"] == "out_of_stock"
    assert updated_404["is_active"] is False
    for v in updated_404["variants"]:
        assert v["in_stock"] is False, f"JD Sports variant {v['sku']} must be cascaded to in_stock=False on 404"
    assert updated_404["last_verified_at"] != "2026-09-01T00:00:00Z", "404 must advance last_verified_at"

    # Scenario C: HTTP 429 / 403 Rate Limit maintains strict immutability (ADR 0008)
    delta_429 = {
        "status": "rate_limited",
        "handle": product_jds["handle"],
        "availability": "in_stock",
        "old_availability": "in_stock",
        "current_source_price": 120.0,
        "old_source_price": 120.0,
        "is_active": True,
        "price_changed": False,
        "stock_changed": False,
        "variant_stock_changed": False,
        "error": "Rate limit retries exhausted"
    }
    updated_429, changed_429 = jdsports_apply(copy.deepcopy(product_jds), delta_429, forex_rate)
    assert changed_429 is False, "Rate limited delta must return has_changed = False"
    assert updated_429["last_verified_at"] == "2026-09-01T00:00:00Z", "Rate limited delta must NOT advance last_verified_at"

    print("  ✅ PASS: JD Sports multi-tier variant inventory shifts mutate cleanly, whole-rupee math is enforced, 404 delistings cascade depletion, and rate limits maintain immutability.")


def test_cross_store_granular_variant_price_and_stock_invariants():
    print("\n[TEST 14] Verifying Cross-Store Granular Variant Price, Anti-Flattening & Fallback Invariants...")
    forex_rate = 95.989567

    stores_to_test = [
        ("coach", coach_apply),
        ("jdsports", jdsports_apply),
        ("footlocker", fl_apply),
        ("jwpei", jwpei_apply),
        ("michaelkors", mk_apply),
        ("nordstrom", nordstrom_apply),
        ("jomashop", jomashop_apply),
        ("_template", template_apply)
    ]

    for store_name, apply_fn in stores_to_test:
        # 1. Anti-Flattening & Granular Mutation Verification
        prod = {
            "id": f"{store_name}_prod_01",
            "handle": f"{store_name}-test-product",
            "title": f"{store_name.title()} Test Product",
            "source_store": store_name,
            "source_price": 100.0,
            "current_price": float(round(100.0 * forex_rate)),
            "availability": "in_stock",
            "is_active": True,
            "last_verified_at": "2026-09-01T00:00:00Z",
            "variants": [
                {
                    "sku": f"{store_name.upper()}-V1-8",
                    "size": "8",
                    "title": "US 8",
                    "in_stock": True,
                    "source_price": 100.0,
                    "price": f"{round(100.0 * forex_rate):.2f}",
                    "price_current": float(round(100.0 * forex_rate))
                },
                {
                    "sku": f"{store_name.upper()}-V2-9",
                    "size": "9",
                    "title": "US 9",
                    "in_stock": True,
                    "source_price": 100.0,
                    "price": f"{round(100.0 * forex_rate):.2f}",
                    "price_current": float(round(100.0 * forex_rate))
                }
            ]
        }

        # Size 8 drops to $80.0, Size 9 remains at $100.0. Parent remains $100.0.
        delta_variant_only = {
            "status": "success",
            "handle": prod["handle"],
            "current_source_price": 100.0,
            "old_source_price": 100.0,
            "price_changed": False,
            "stock_changed": False,
            "variant_stock_changed": False,
            "variant_price_changed": True,
            "changed_variant_prices": [
                {
                    "sku": f"{store_name.upper()}-V1-8",
                    "size": "8",
                    "old_source_price": 100.0,
                    "new_source_price": 80.0
                }
            ],
            "availability": "in_stock",
            "variants_delta": [
                {"sku": f"{store_name.upper()}-V1-8", "size": "8", "available": True, "price_usd": 80.0},
                {"sku": f"{store_name.upper()}-V2-9", "size": "9", "available": True, "price_usd": 100.0}
            ]
        }

        updated, has_changed = apply_fn(copy.deepcopy(prod), delta_variant_only, forex_rate)
        assert has_changed is True, f"[{store_name}] Variant-only price shift must set has_changed = True"
        if store_name == "nordstrom":
            assert updated["source_price"] == 80.0, f"[{store_name}] Parent source_price should synchronize to min variant price 80.0"
            assert updated.get("price_range_usd") == {"min": 80.0, "max": 100.0}, f"[{store_name}] price_range_usd mismatch"
        else:
            assert updated["source_price"] == 100.0, f"[{store_name}] Parent source_price must remain 100.0"

        v1 = [v for v in updated["variants"] if "V1-8" in v["sku"] or v.get("size") == "8"][0]
        v2 = [v for v in updated["variants"] if "V2-9" in v["sku"] or v.get("size") == "9"][0]

        # Check Variant 1: Mutated to 80.0
        assert v1["source_price"] == 80.0, f"[{store_name}] Variant 1 source_price should be 80.0, got {v1.get('source_price')}"
        expected_v1_inr = float(round(80.0 * forex_rate))
        assert v1["price_current"] == expected_v1_inr, f"[{store_name}] Variant 1 price_current mismatch: {v1.get('price_current')} vs {expected_v1_inr}"
        assert v1["price"] == f"{expected_v1_inr:.2f}", f"[{store_name}] Variant 1 price string mismatch: {v1.get('price')} vs {expected_v1_inr:.2f}"

        # Check Variant 2: Unchanged at 100.0 (Anti-flattening invariant)
        assert v2["source_price"] == 100.0, f"[{store_name}] Variant 2 source_price flattened/corrupted: {v2.get('source_price')}"
        expected_v2_inr = float(round(100.0 * forex_rate))
        assert v2["price_current"] == expected_v2_inr, f"[{store_name}] Variant 2 price_current corrupted: {v2.get('price_current')}"

        # 2. Uniform Fallback Synchronization Verification
        # When parent source_price shifts to $150.0 with no explicit per-variant delta
        delta_parent_uniform = {
            "status": "success",
            "handle": prod["handle"],
            "current_source_price": 150.0,
            "old_source_price": 100.0,
            "price_changed": True,
            "stock_changed": False,
            "availability": "in_stock",
            "variants_delta": []
        }

        updated_uniform, has_changed_uniform = apply_fn(copy.deepcopy(prod), delta_parent_uniform, forex_rate)
        assert has_changed_uniform is True, f"[{store_name}] Parent price shift must return has_changed = True"
        assert updated_uniform["source_price"] == 150.0
        expected_parent_inr = float(round(150.0 * forex_rate))
        assert updated_uniform["current_price"] == expected_parent_inr

        for v in updated_uniform["variants"]:
            assert v["source_price"] == 150.0, f"[{store_name}] Uniform sync failed to update variant source_price to 150.0"
            assert v["price_current"] == expected_parent_inr, f"[{store_name}] Uniform sync failed for price_current"
            assert v["price"] == f"{expected_parent_inr:.2f}", f"[{store_name}] Uniform sync failed for price string"

    print("  ✅ PASS: All 8 store delta modules preserve granular variant price anti-flattening, tri-field integrity, and uniform fallback sync.")


def test_adversarial_variant_price_divergence_and_shopify_events():
    print("\n[TEST 15] Verifying Adversarial Variant Matching, Coach Footwear Tokens & Shopify Event Dispatch...")
    forex_rate = 95.989567

    # 1. Coach Footwear Size Matching Adversarial Tokens
    assert matches_coach_size("7", "US 7 / UK 5", "CFX45-7") is True
    assert matches_coach_size("7D", "US 7D / UK 7D", "CFZ93 BLK  8   D-7D") is True
    assert matches_coach_size("7", "7D", "CFX45-7D") is True
    assert matches_coach_size("7", "US 7.5 / UK 5.5", "CFX45-7.5") is False
    assert matches_coach_size("8", "US 8 / UK 6", "CFX45-8") is True
    assert matches_coach_size("8.5", "US 8 / UK 6", "CFX45-8") is False

    # 2. Dispatcher Integration & Shopify Delta Event Enqueue Contract
    # Test that poll_single_product records variant_price_changed and changed_variant_prices
    prod_dispatch_stub = {
        "id": "172567dc87d36e1b",
        "handle": "big-kids-nike-air-force-1-low-casual-shoes-white-pink-rise-ct3839_124",
        "source_store": "jdsports"
    }

    # Mock dynamic dispatcher store module returning variant price divergence
    class MockVariantStoreModule:
        @staticmethod
        def check_price_and_stock(product, client=None, store_name="jdsports", rate_limiter=None):
            return {
                "status": "success",
                "handle": product.get("handle"),
                "current_source_price": 90.0,
                "old_source_price": 90.0,
                "availability": "in_stock",
                "old_availability": "in_stock",
                "price_changed": False,
                "stock_changed": False,
                "variant_stock_changed": False,
                "changed_variants": [],
                "variant_price_changed": True,
                "changed_variant_prices": [
                    {
                        "sku": "CT3839_124-3.5Y",
                        "size": "3.5Y",
                        "old_source_price": 90.0,
                        "new_source_price": 75.0
                    }
                ],
                "variants_delta": [
                    {"sku": "CT3839_124-3.5Y", "size": "3.5Y", "available": True, "price_usd": 75.0}
                ],
                "elapsed_ms": 12.0
            }

        @staticmethod
        def apply_delta_to_product(product, delta_result, forex_rate):
            return jdsports_apply(product, delta_result, forex_rate)

    mock_client = httpx.Client()
    # Execute poll_single_product in dry_run=False mode to test event persistence
    res = poll_single_product(
        product_stub=prod_dispatch_stub,
        store_mod=MockVariantStoreModule,
        client=mock_client,
        forex_rate=forex_rate,
        delay_seconds=0.0,
        dry_run=False,
        store_name="jdsports"
    )
    mock_client.close()

    assert res["status"] == "success"
    assert res["has_changed"] is True
    assert res["variant_price_changed"] is True
    assert len(res["changed_variant_prices"]) == 1
    assert res["changed_variant_prices"][0]["sku"] == "CT3839_124-3.5Y"
    assert res["changed_variant_prices"][0]["new_source_price"] == 75.0

    # Read the emitted event from delta events queue
    events = read_delta_events()
    matching_events = [e for e in events if e.get("product_id") == "172567dc87d36e1b"]
    assert len(matching_events) >= 1, "Shopify delta event must be enqueued on variant price change"
    latest_evt = matching_events[-1]
    assert latest_evt["variant_price_changed"] is True, "Shopify event must record variant_price_changed=True"
    assert len(latest_evt["changed_variant_prices"]) == 1, "Shopify event must capture changed_variant_prices list"
    assert latest_evt["changed_variant_prices"][0]["new_source_price"] == 75.0
    assert latest_evt["shopify_sync_pending"] is True

    print("  ✅ PASS: Coach footwear size matching regex and Shopify delta event queue for variant pricing verified.")


def test_jomashop_delta_integration():
    print("\n[TEST 16] Verifying Jomashop Delta Engine GraphQL Polling, Stock Depletion Cascade & Circuit Breaker...")
    forex_rate = 95.989567
    reset_rate_limiter()

    sample_product = {
        "id": "jomashop_tissot_prx_01",
        "handle": "tissot-prx-powermatic-80-blue-dial-watch-t1374071104100",
        "title": "Tissot PRX Powermatic 80 Blue Dial Watch",
        "source_store": "jomashop",
        "vendor": "Tissot",
        "source_sku": "T1374071104100",
        "source_price": 725.0,
        "current_price": float(round(725.0 * forex_rate)),
        "availability": "out_of_stock",
        "is_active": False,
        "last_verified_at": "2026-09-01T00:00:00Z",
        "variants": [
            {
                "sku": "T1374071104100",
                "in_stock": False,
                "source_price": 725.0,
                "price": f"{round(725.0 * forex_rate):.2f}",
                "price_current": float(round(725.0 * forex_rate)),
                "title": "40 mm - Blue / Stainless Steel"
            }
        ]
    }

    # 1. Test check_price_and_stock() on 200 OK price update and stock flip (OOS -> IN_STOCK, $725 -> $595)
    class MockGqlSuccessResponse:
        status_code = 200
        headers = {"content-type": "application/json"}
        def raise_for_status(self): pass
        def json(self):
            return {
                "data": {
                    "products": {
                        "items": [
                            {
                                "id": "98765",
                                "sku": "T1374071104100",
                                "url_key": "tissot-prx-powermatic-80-blue-dial-watch-t1374071104100",
                                "stock_status": "IN_STOCK",
                                "price_range": {
                                    "minimum_price": {
                                        "regular_price": {"value": 725.0, "currency": "USD"},
                                        "final_price": {"value": 595.0, "currency": "USD"},
                                        "msrp_price": {"value": 725.0, "currency": "USD"}
                                    }
                                }
                            }
                        ]
                    }
                }
            }

    class MockGqlSuccessClient:
        def post(self, url, json=None, headers=None):
            return MockGqlSuccessResponse()

    res_success = jomashop_check(sample_product, client=MockGqlSuccessClient(), store_name="jomashop")
    assert res_success["status"] == "success", f"Expected success, got {res_success['status']}"
    assert res_success["current_source_price"] == 595.0, f"Expected $595.0, got {res_success['current_source_price']}"
    assert res_success["old_source_price"] == 725.0
    assert res_success["price_changed"] is True
    assert res_success["stock_changed"] is True
    assert res_success["availability"] == "in_stock"
    assert res_success["old_availability"] == "out_of_stock"
    assert res_success["is_active"] is True
    assert len(res_success["variants_delta"]) == 1
    assert res_success["variants_delta"][0]["available"] is True
    assert res_success["variants_delta"][0]["price_usd"] == 595.0

    # Test apply_delta_to_product() on 200 OK success
    updated_prod, changed = jomashop_apply(copy.deepcopy(sample_product), res_success, forex_rate)
    assert changed is True, "apply_delta_to_product must flag has_changed = True"
    assert updated_prod["source_price"] == 595.0
    expected_inr = float(round(595.0 * forex_rate))
    assert updated_prod["current_price"] == expected_inr
    assert updated_prod["current_price"] % 1 == 0, "INR price must be whole-rupee (no fractional paise)"
    assert updated_prod["compare_at_price"] == float(round(725.0 * forex_rate))
    assert updated_prod["availability"] == "in_stock"
    assert updated_prod["is_active"] is True
    assert updated_prod["variants"][0]["in_stock"] is True
    assert updated_prod["variants"][0]["source_price"] == 595.0
    assert updated_prod["variants"][0]["price_current"] == expected_inr
    assert updated_prod["variants"][0]["price"] == f"{expected_inr:.2f}"
    assert updated_prod["last_verified_at"] != "2026-09-01T00:00:00Z", "Success MUST stamp last_verified_at"
    assert updated_prod["shopify_sync_pending"] is True

    # 2. Test selective timestamp stamping:
    # A. Rate limited (429 retries exhausted) -> NEVER stamp last_verified_at, has_changed = False
    delta_429 = {
        "status": "rate_limited",
        "handle": sample_product["handle"],
        "availability": "out_of_stock",
        "old_availability": "out_of_stock",
        "current_source_price": 725.0,
        "old_source_price": 725.0,
        "error": "Rate limit retries exhausted (HTTP 429)"
    }
    prod_429, changed_429 = jomashop_apply(copy.deepcopy(sample_product), delta_429, forex_rate)
    assert changed_429 is False, "Rate limited delta must return has_changed = False"
    assert prod_429["last_verified_at"] == "2026-09-01T00:00:00Z", "Rate limited check MUST NOT stamp last_verified_at"

    # B. Network/5xx Error -> NEVER stamp last_verified_at, has_changed = False
    delta_error = {
        "status": "error",
        "handle": sample_product["handle"],
        "availability": "out_of_stock",
        "old_availability": "out_of_stock",
        "current_source_price": 725.0,
        "old_source_price": 725.0,
        "error": "Timeout connecting to GraphQL endpoint"
    }
    prod_err, changed_err = jomashop_apply(copy.deepcopy(sample_product), delta_error, forex_rate)
    assert changed_err is False, "Error delta must return has_changed = False"
    assert prod_err["last_verified_at"] == "2026-09-01T00:00:00Z", "Error check MUST NOT stamp last_verified_at"

    # 3. Test HTTP 404 delisting stock depletion cascade (ADR 0015):
    in_stock_watch = copy.deepcopy(updated_prod)
    in_stock_watch["last_verified_at"] = "2026-09-01T00:00:00Z"

    # A. Mock HTTP 404 client response in check_price_and_stock()
    class Mock404Response:
        status_code = 404
        headers = {}
        def raise_for_status(self): raise httpx.HTTPStatusError("Not Found", request=None, response=self)

    class Mock404Client:
        def post(self, url, json=None, headers=None):
            return Mock404Response()

    res_404 = jomashop_check(in_stock_watch, client=Mock404Client(), store_name="jomashop")
    assert res_404["status"] == "not_found", f"Expected not_found, got {res_404['status']}"
    assert res_404["availability"] == "out_of_stock"
    assert res_404["old_availability"] == "in_stock", "404 check must preserve old_availability"
    assert res_404["current_source_price"] == 595.0, "404 check must preserve current_source_price"
    assert res_404["old_source_price"] == 595.0, "404 check must preserve old_source_price"
    assert res_404["stock_changed"] is True
    assert res_404["is_active"] is False

    # B. Apply 404 delta to product -> Depletion cascade to all variants + stamps timestamp
    prod_delisted, changed_delisted = jomashop_apply(copy.deepcopy(in_stock_watch), res_404, forex_rate)
    assert changed_delisted is True, "404 delisting must flag has_changed = True"
    assert prod_delisted["availability"] == "out_of_stock"
    assert prod_delisted["is_active"] is False
    # CRITICAL ADR 0015: variant stock must cascade to False
    for v in prod_delisted["variants"]:
        assert v["in_stock"] is False, f"Variant {v['sku']} must be depleted on 404"
    assert prod_delisted["last_verified_at"] != "2026-09-01T00:00:00Z", "404 delisting MUST advance last_verified_at"
    assert prod_delisted["shopify_sync_pending"] is True

    # 4. Test HTTP 429 rate limit backoff and anti-thundering-herd circuit breaker tripping via trip_circuit_breaker() (ADR 0010)
    configure_store_rate_limits("jomashop", requests_per_second=2.0, delay_seconds=0.5)
    assert is_circuit_open("jomashop") is False

    class Mock429GqlResponse:
        status_code = 429
        headers = {"Retry-After": "2"}
        def raise_for_status(self): pass

    class Mock429GqlClient:
        def post(self, url, json=None, headers=None):
            return Mock429GqlResponse()

    limiter_joma = create_store_limiter("jomashop")
    res_breaker = jomashop_check(sample_product, client=Mock429GqlClient(), store_name="jomashop", rate_limiter=limiter_joma)
    assert res_breaker["status"] == "rate_limited"
    assert is_circuit_open("jomashop") is True, "Circuit breaker must be open after HTTP 429 response"
    assert get_cooldown_remaining("jomashop") > 0.0, "Cooldown must be active on circuit breaker trip"

    reset_rate_limiter()
    print("  ✅ PASS: Jomashop GraphQL 200 OK price/stock updates, selective timestamping, 404 delisting cascade, and 429 circuit tripping verified.")


def run_all_tests():
    print("=" * 72)
    print("DELTA ENGINE INTEGRATION & UNIT TEST SUITE (MULTI-STORE EDITION)")
    print("=" * 72)

    test_config_loading()
    test_interval_and_timestamp_filtering()
    test_delta_mutation_and_shopify_queue()
    test_rate_limiter_and_circuit_breaker()
    test_browser_fingerprinting()
    test_resilience_and_selective_timestamping()
    test_live_jwpei_connectivity()
    test_multi_store_isolation_and_429_circuit_breaking()
    test_dispatcher_resilience_and_contracts()
    test_footlocker_delta_cascade_and_selective_timestamping()
    test_nordstrom_multicolorway_delta_and_price_range_sync()
    test_coach_multivariant_delta_and_scene7_integrity()
    test_jdsports_multitier_delta_and_depletion_cascade()
    test_cross_store_granular_variant_price_and_stock_invariants()
    test_adversarial_variant_price_divergence_and_shopify_events()
    test_jomashop_delta_integration()

    print("\n" + "=" * 72)
    print("ALL TESTS PASSED WITH 100% SUCCESS")
    print("=" * 72)


if __name__ == "__main__":
    run_all_tests()


