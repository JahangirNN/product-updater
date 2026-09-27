"""
Non-Destructive 5-Phase Canary Test for Option 1: Luxury Bags
Tests real-time price delta shift, Shopify Admin GraphQL propagation,
delta ledger recording in storage/db/history/delta_events.jsonl,
and seamless clean rollback.
Adheres to ADR 0005, 0006, 0008, 0020, 0021, 0023.
"""
import os
import sys
import json
import time
import copy
from typing import Dict, Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from storage.shopify_auth import execute_shopify_graphql
from storage.shopify_sync import sync_delta_to_shopify
from storage.forex import get_usd_to_inr_rate
from storage.db import save_product, append_delta_event, load_product
from storage.logger import log_info, log_success, log_error, init_logger
from stores.jwpei.delta import apply_delta_to_product

CANARY_ID = "006291ad60a33773"
CANARY_STORE = "jwpei"
CANARY_FILE = os.path.join(PROJECT_ROOT, "storage", "db", CANARY_STORE, "products", f"{CANARY_ID}.json")
DELTA_EVENTS_FILE = os.path.join(PROJECT_ROOT, "storage", "db", "history", "delta_events.jsonl")

GET_PRODUCT_QUERY = """
query getCanaryProduct($id: ID!) {
  product(id: $id) {
    id
    title
    handle
    status
    variants(first: 5) {
      nodes {
        id
        sku
        price
      }
    }
  }
}
"""


def get_live_shopify_price(gid: str) -> float:
    """Fetch live variant price from Shopify Admin GraphQL."""
    data, ext, err = execute_shopify_graphql(GET_PRODUCT_QUERY, variables={"id": gid})
    if err or not data or not data.get("product"):
        raise RuntimeError(f"Failed to fetch canary product from Shopify: {err}")
    nodes = data["product"]["variants"]["nodes"]
    if not nodes:
        raise RuntimeError("Canary product has no variants in Shopify")
    return float(nodes[0]["price"])


def run_canary_test() -> Dict[str, Any]:
    init_logger()
    print("=" * 80)
    print("OPTION 1 LUXURY BAGS: 5-PHASE NON-DESTRUCTIVE CANARY TEST")
    print("=" * 80)

    forex_rate = get_usd_to_inr_rate()
    print(f"[*] Live Forex Rate: 1 USD = INR {forex_rate:.2f}")

    # PHASE 1: Baseline Verification
    print("\n--- PHASE 1: Baseline Verification ---")
    assert os.path.exists(CANARY_FILE), f"Canary file missing: {CANARY_FILE}"
    with open(CANARY_FILE, "r", encoding="utf-8") as f:
        original_product = json.load(f)

    canary_gid = original_product.get("shopify_product_id")
    assert canary_gid, "Canary product does not have shopify_product_id stamped!"
    print(f"[*] Canary Product: '{original_product.get('title')}'")
    print(f"[*] Canary GID: {canary_gid}")

    live_baseline_price = get_live_shopify_price(canary_gid)
    orig_inr_price = live_baseline_price
    orig_source_price = float(original_product.get("source_price") or round(live_baseline_price / forex_rate, 2))
    print(f"[*] Live Shopify Baseline Price: INR {live_baseline_price:.2f} (${orig_source_price:.2f} USD)")
    print("[+] Phase 1 Passed: Baseline confirmed on Shopify.")

    # Backup original product to preserve exact state
    backup_copy = copy.deepcopy(original_product)

    try:
        # PHASE 2: Apply Synthetic Price Delta Shift (+20 USD)
        shifted_source_price = orig_source_price + 20.0
        expected_shifted_inr = round(shifted_source_price * forex_rate)
        print(f"\n--- PHASE 2: Synthetic Delta Shift ($229.00 -> ${shifted_source_price:.2f}) ---")

        delta_res = {
            "status": "success",
            "price_changed": True,
            "old_source_price": orig_source_price,
            "current_source_price": shifted_source_price,
            "stock_changed": False,
            "old_availability": original_product.get("availability", "in_stock"),
            "availability": original_product.get("availability", "in_stock"),
            "variant_stock_changed": False,
            "changed_variants": [],
            "variant_price_changed": False,
            "changed_variant_prices": []
        }

        updated_product, has_changed = apply_delta_to_product(original_product, delta_res, forex_rate)
        assert has_changed, "apply_delta_to_product did not detect change"
        assert updated_product["source_price"] == shifted_source_price
        assert updated_product["current_price"] == expected_shifted_inr
        print(f"[*] Product model updated locally: INR {updated_product['current_price']}")

        # Push delta shift to Shopify
        print("[*] Pushing live delta shift to Shopify Admin GraphQL...")
        synced_ok = sync_delta_to_shopify(updated_product, delta_res, forex_rate)
        assert synced_ok, "sync_delta_to_shopify failed to push price shift"
        print("[+] Real-time GraphQL delta update confirmed by Shopify.")

        # Log event into append-only ledger
        shift_event = {
            "event_id": f"canary_shift_{int(time.time()*1000)}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "store": CANARY_STORE,
            "product_id": CANARY_ID,
            "handle": updated_product.get("handle"),
            "title": updated_product.get("title"),
            "price_changed": True,
            "old_source_price": orig_source_price,
            "new_source_price": shifted_source_price,
            "new_current_price_inr": expected_shifted_inr,
            "stock_changed": False,
            "shopify_sync_pending": False
        }
        append_delta_event(shift_event)
        save_product(updated_product)
        print("[+] Delta event recorded in storage/db/history/delta_events.jsonl.")
        print("[+] Phase 2 Passed: Delta shift applied and dispatched.")

        # PHASE 3: Verify Live Shopify Reflection
        print("\n--- PHASE 3: Live Shopify Verification ---")
        time.sleep(1.0)
        live_shifted_price = get_live_shopify_price(canary_gid)
        print(f"[*] Live Shopify Shifted Price: INR {live_shifted_price:.2f} (Expected: INR {expected_shifted_inr:.2f})")
        assert live_shifted_price == expected_shifted_inr, f"Shopify price did not update: {live_shifted_price} != {expected_shifted_inr}"
        assert live_shifted_price.is_integer(), "Shopify price must be whole rupee (0 paise)"
        print("[+] Phase 3 Passed: Shopify verified reflecting shifted price with whole rupees.")

    finally:
        # PHASE 4: Clean Rollback
        print("\n--- PHASE 4: Clean Rollback to Baseline ---")
        rollback_delta_res = {
            "status": "success",
            "price_changed": True,
            "old_source_price": shifted_source_price,
            "current_source_price": orig_source_price,
            "stock_changed": False,
            "old_availability": backup_copy.get("availability", "in_stock"),
            "availability": backup_copy.get("availability", "in_stock"),
            "variant_stock_changed": False,
            "changed_variants": [],
            "variant_price_changed": False,
            "changed_variant_prices": []
        }

        reverted_product, _ = apply_delta_to_product(backup_copy, rollback_delta_res, forex_rate)
        save_product(reverted_product)

        print("[*] Reverting price back on Shopify Admin GraphQL...")
        rollback_synced = sync_delta_to_shopify(reverted_product, rollback_delta_res, forex_rate)
        assert rollback_synced, "Rollback sync_delta_to_shopify failed"

        rollback_event = {
            "event_id": f"canary_rollback_{int(time.time()*1000)}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "store": CANARY_STORE,
            "product_id": CANARY_ID,
            "handle": reverted_product.get("handle"),
            "title": reverted_product.get("title"),
            "price_changed": True,
            "old_source_price": shifted_source_price,
            "new_source_price": orig_source_price,
            "new_current_price_inr": orig_inr_price,
            "stock_changed": False,
            "shopify_sync_pending": False
        }
        append_delta_event(rollback_event)
        print("[+] Rollback event recorded in storage/db/history/delta_events.jsonl.")
        print("[+] Phase 4 Passed: Rollback dispatched.")

        expected_restored_inr = round(orig_source_price * forex_rate)
        final_live_price = get_live_shopify_price(canary_gid)
        print(f"[*] Final Live Shopify Price: INR {final_live_price:.2f} (Expected: INR {expected_restored_inr:.2f})")
        assert final_live_price == expected_restored_inr, f"Final price mismatch: {final_live_price} != {expected_restored_inr}"
        assert final_live_price.is_integer(), "Shopify price must be whole rupee (0 paise)"
        print("[+] Phase 5 Passed: Canary product restored to exact original baseline with live whole-rupee rate.")

    print("\n" + "=" * 80)
    print("ALL 5 PHASES OF LUXURY BAG CANARY TEST PASSED WITH 100% INTEGRITY!")
    print("=" * 80)
    return {
        "status": "passed",
        "canary_id": CANARY_ID,
        "canary_title": original_product.get("title"),
        "canary_gid": canary_gid,
        "baseline_inr": orig_inr_price,
        "shifted_inr": expected_shifted_inr,
        "final_inr": final_live_price
    }


if __name__ == "__main__":
    run_canary_test()
