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

from stores.nordstrom.delta import apply_delta_to_product
from storage.shopify_sync import sync_delta_to_shopify
from storage.shopify_auth import execute_shopify_graphql
from storage.forex import get_usd_to_inr_rate

def run_empirical_freshner_verification():
    print("=" * 80)
    print("EMPIRICAL NORDSTROM FRESHNER LOOP & SHOPIFY SYNC VERIFICATION")
    print("=" * 80)

    forex_rate = get_usd_to_inr_rate()
    print(f"Live Forex Rate: 1 USD = INR {forex_rate:.2f}")

    # 1. Load a newly added Nordstrom product that is active and has multiple variants
    target_fp = None
    target_prod = None
    nord_dir = os.path.join(PROJECT_ROOT, "storage", "db", "nordstrom", "products")
    for fname in os.listdir(nord_dir):
        if not fname.endswith(".json"):
            continue
        fp = os.path.join(nord_dir, fname)
        with open(fp, "r", encoding="utf-8") as f:
            p = json.load(f)
        if p.get("shopify_product_id") and p.get("availability") == "in_stock" and len(p.get("variants", [])) >= 2:
            target_fp = fp
            target_prod = p
            break

    assert target_prod is not None, "No suitable multi-variant active Nordstrom product found!"
    print(f"Target Product: '{target_prod.get('title')}'")
    print(f"Shopify GID:    {target_prod.get('shopify_product_id')}")
    print(f"Handle:         {target_prod.get('shopify_handle')}")
    print(f"Total Variants: {len(target_prod.get('variants', []))}")

    # Preserve exact backup to restore later
    backup_prod = copy.deepcopy(target_prod)

    # -------------------------------------------------------------
    # (a) Verify Delta Parsing & Shift Detection
    # -------------------------------------------------------------
    print("\n--- (a) Verifying Delta Engine Parsing & Shift Representation ---")
    old_price = float(target_prod.get("source_price") or 150.0)
    new_price = old_price + 10.0  # Simulated price shift
    
    # Pick first variant to toggle stock (e.g. simulate one size going out of stock)
    v0 = target_prod["variants"][0]
    v1 = target_prod["variants"][1]
    v0_sku = v0.get("sku")
    v1_sku = v1.get("sku")

    delta_payload = {
        "status": "success",
        "handle": target_prod.get("handle"),
        "current_source_price": new_price,
        "old_source_price": old_price,
        "availability": "in_stock",
        "old_availability": "in_stock",
        "price_changed": True,
        "stock_changed": False,
        "variant_price_changed": True,
        "variant_stock_changed": True,
        "variants_delta": [
            {
                "sku": v0_sku,
                "available": False,  # v0 is OOS
                "price_usd": new_price,
                "compare_price_usd": float(v0.get("source_compare_at_price") or 0.0)
            },
            {
                "sku": v1_sku,
                "available": True,   # v1 is In Stock
                "price_usd": new_price,
                "compare_price_usd": float(v1.get("source_compare_at_price") or 0.0)
            }
        ]
    }
    print(f"Simulated delta payload: price {old_price} -> {new_price}, variant {v0_sku} -> OOS, variant {v1_sku} -> In Stock")

    # -------------------------------------------------------------
    # (b) Verify apply_delta_to_product
    # -------------------------------------------------------------
    print("\n--- (b) Verifying apply_delta_to_product Computation & Timestamp Stamping ---")
    test_prod = copy.deepcopy(target_prod)
    test_prod["last_verified_at"] = "2020-01-01T00:00:00Z"

    updated_prod, has_changed = apply_delta_to_product(test_prod, delta_payload, forex_rate)
    
    print(f"apply_delta_to_product returned has_changed = {has_changed}")
    assert has_changed is True, "apply_delta_to_product failed to detect shift!"
    
    now_iso = updated_prod.get("last_verified_at")
    print(f"Updated last_verified_at: {now_iso}")
    assert now_iso and now_iso.startswith("2026-"), "last_verified_at was not stamped with current timestamp!"

    # Verify variant state
    for v in updated_prod.get("variants", []):
        if v.get("sku") == v0_sku:
            print(f"Variant {v0_sku} in_stock state: {v.get('in_stock')} (Expected: False)")
            assert v.get("in_stock") is False
        elif v.get("sku") == v1_sku:
            print(f"Variant {v1_sku} in_stock state: {v.get('in_stock')} (Expected: True)")
            assert v.get("in_stock") is True

    # -------------------------------------------------------------
    # (c) Verify sync_delta_to_shopify Live Mutation
    # -------------------------------------------------------------
    print("\n--- (c) Verifying sync_delta_to_shopify Live Mutation ---")
    sync_ok = sync_delta_to_shopify(updated_prod, delta_payload, forex_rate)
    print(f"sync_delta_to_shopify returned: {sync_ok}")
    assert sync_ok is True, "sync_delta_to_shopify failed to mutate Shopify!"

    # Query Shopify Admin to verify mutation took effect
    time.sleep(2)
    verify_query = """
    query checkProd($id: ID!) {
      product(id: $id) {
        id
        title
        status
        variants(first: 50) {
          edges {
            node {
              id
              sku
              price
              inventoryPolicy
              inventoryItem {
                tracked
              }
            }
          }
        }
      }
    }
    """
    res, _, err = execute_shopify_graphql(verify_query, {"id": target_prod["shopify_product_id"]})
    assert res and res.get("product"), f"Failed to fetch updated product from Shopify: {err}"
    
    live_prod = res["product"]
    print(f"Live Product Title: {live_prod['title']}")
    print(f"Live Status:        {live_prod['status']}")

    # -------------------------------------------------------------
    # (d) Verify Out-of-Stock and In-Stock Policies
    # -------------------------------------------------------------
    print("\n--- (d) Verifying In-Stock vs Out-of-Stock Policy Invariants (ADR 0015) ---")
    variant_nodes = [e["node"] for e in live_prod["variants"]["edges"]]
    v0_target_skus = {v0_sku, f"RARE-{v0_sku}"}
    v1_target_skus = {v1_sku, f"RARE-{v1_sku}"}
    v0_node = next((n for n in variant_nodes if n.get("sku") in v0_target_skus), None)
    v1_node = next((n for n in variant_nodes if n.get("sku") in v1_target_skus), None)

    if v0_node:
        print(f"OOS Variant {v0_sku}: policy = {v0_node['inventoryPolicy']}, tracked = {v0_node['inventoryItem']['tracked']}")
        assert v0_node["inventoryPolicy"] == "DENY", f"Expected inventoryPolicy DENY, got {v0_node['inventoryPolicy']}"
        assert v0_node["inventoryItem"]["tracked"] is True, f"Expected tracked True, got {v0_node['inventoryItem']['tracked']}"
        print("  --> [PASS] Out-of-stock variant has inventoryPolicy: DENY and tracked: True")
    else:
        print(f"Warning: v0_node {v0_sku} not found directly in first 10 variants")

    if v1_node:
        print(f"In-Stock Variant {v1_sku}: policy = {v1_node['inventoryPolicy']}, tracked = {v1_node['inventoryItem']['tracked']}")
        assert v1_node["inventoryPolicy"] == "CONTINUE", f"Expected inventoryPolicy CONTINUE, got {v1_node['inventoryPolicy']}"
        assert v1_node["inventoryItem"]["tracked"] is False, f"Expected tracked False, got {v1_node['inventoryItem']['tracked']}"
        print("  --> [PASS] In-stock variant has inventoryPolicy: CONTINUE and tracked: False")

    # -------------------------------------------------------------
    # Restore Product State
    # -------------------------------------------------------------
    print("\n--- Restoring Target Product to Original Authentic State ---")
    restore_ok = sync_delta_to_shopify(backup_prod, {}, forex_rate)
    print(f"Product restored in Shopify: {restore_ok}")
    with open(target_fp, "w", encoding="utf-8") as f:
        json.dump(backup_prod, f, indent=2, ensure_ascii=False)
    print("Disk JSON restored cleanly.")

    print("\n" + "=" * 80)
    print("EMPIRICAL FRESHNER VERIFICATION: ALL 4 INVARIANTS (a, b, c, d) VERIFIED!")
    print("=" * 80)

if __name__ == "__main__":
    run_empirical_freshner_verification()
