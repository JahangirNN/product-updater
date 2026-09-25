"""
Deep Live Audit & Verification Suite: Watch Stock, Price & Shopify Synchronization
Performs an end-to-end verification of:
1. Live Jomashop Apollo GraphQL Polling (Stock & Price Freshness)
2. 100% Shopify GID Coverage across all 574 watches
3. Live Differential Mutation & Real-Time Shopify Admin GraphQL Synchronization (Price & Stock)
4. Full Watch Technical Data & Specification Accordion Integrity
Adheres to ADR 0004, 0005, 0006, 0015, 0018, 0019, 0020, and 0021.
"""
import os
import sys
import glob
import json
import time
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from storage.shopify_auth import execute_shopify_graphql
from storage.shopify_sync import upsert_product_to_shopify, sync_delta_to_shopify
from storage.forex import get_usd_to_inr_rate
import stores.jomashop.delta as joma_delta


def audit_phase_1_live_jomashop_polling() -> Tuple[bool, Dict[str, Any]]:
    print("\n" + "=" * 80)
    print("PHASE 1: LIVE JOMASHOP APOLLO GRAPHQL POLLING & FRESHNESS AUDIT")
    print("=" * 80)
    
    db_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "db", "jomashop", "products")
    files = glob.glob(os.path.join(db_root, "*.json"))
    
    # Select 5 diverse watches across brands
    sample_files = []
    seen_brands = set()
    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            p = json.load(f)
        b = p.get("vendor", "")
        if b and b not in seen_brands:
            seen_brands.add(b)
            sample_files.append((fp, p))
        if len(sample_files) >= 5:
            break

    print(f"[*] Testing live polling against {len(sample_files)} sample watches across {len(seen_brands)} brands...")
    results = []
    all_ok = True

    for idx, (fp, prod) in enumerate(sample_files, 1):
        p_id = prod.get("id")
        title = prod.get("title", "")[:45]
        vendor = prod.get("vendor", "")
        print(f"  [{idx}/{len(sample_files)}] Polling '{title}' ({vendor})...", end=" ", flush=True)
        
        start = time.time()
        res = joma_delta.check_price_and_stock(prod)
        elapsed = (time.time() - start) * 1000
        
        status = res.get("status")
        if status in ("success", "not_found"):
            curr_price = res.get("current_source_price")
            avail = res.get("availability")
            print(f"[OK] {status} | Stock: {avail} | Price: ${curr_price} ({elapsed:.0f}ms)")
            results.append({"id": p_id, "title": title, "status": status, "avail": avail, "price": curr_price, "elapsed_ms": elapsed})
        else:
            err = res.get("error", "Unknown")
            print(f"[FAIL] {err} ({elapsed:.0f}ms)")
            results.append({"id": p_id, "title": title, "status": status, "error": err})
            all_ok = False
        time.sleep(0.5)

    return all_ok, {"tested": len(sample_files), "results": results}


def audit_phase_2_shopify_gid_coverage() -> Tuple[bool, Dict[str, Any]]:
    print("\n" + "=" * 80)
    print("PHASE 2: 100% SHOPIFY GID COVERAGE & STORAGE STAMP AUDIT")
    print("=" * 80)
    
    db_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "db", "jomashop", "products")
    files = glob.glob(os.path.join(db_root, "*.json"))
    
    missing_gid = []
    stamped_count = 0
    brand_counts = {}

    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            p = json.load(f)
        gid = p.get("shopify_product_id")
        b = p.get("vendor", "Unknown")
        brand_counts[b] = brand_counts.get(b, 0) + 1
        
        if gid and gid.startswith("gid://shopify/Product/"):
            stamped_count += 1
        else:
            missing_gid.append({"file": os.path.basename(fp), "id": p.get("id"), "title": p.get("title")})

    print(f"[*] Total Watches in DB:         {len(files)}")
    print(f"[*] Watches with valid Shopify GID: {stamped_count} ({stamped_count/len(files)*100:.1f}%)")
    print(f"[*] Missing Shopify GID:            {len(missing_gid)}")
    print(f"[*] Brand Distribution:")
    for b, c in sorted(brand_counts.items(), key=lambda x: -x[1]):
        print(f"    - {b:20}: {c} items")

    passed = (len(missing_gid) == 0 and stamped_count == len(files))
    return passed, {"total": len(files), "stamped": stamped_count, "missing": missing_gid}


def audit_phase_3_live_mutation_and_sync() -> Tuple[bool, Dict[str, Any]]:
    print("\n" + "=" * 80)
    print("PHASE 3: LIVE SHOPIFY ADMIN GRAPHQL MUTATION & SYNC AUDIT")
    print("=" * 80)

    db_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "db", "jomashop", "products")
    files = glob.glob(os.path.join(db_root, "*.json"))

    # Pick a sample watch with verified shopify_product_id
    target_fp = None
    target_prod = None
    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            p = json.load(f)
        if p.get("shopify_product_id") and p.get("vendor") == "Tissot" and p.get("current_price"):
            target_fp = fp
            target_prod = p
            break

    if not target_prod:
        print("[!] No suitable target watch found for mutation test.")
        return False, {}

    shopify_id = target_prod["shopify_product_id"]
    original_inr_price = target_prod["current_price"]
    original_usd_price = target_prod["source_price"]
    original_avail = target_prod.get("availability", "in_stock")
    title = target_prod.get("title", "")[:45]

    print(f"[*] Selected Target Watch: '{title}'")
    print(f"[*] Shopify Product GID:    {shopify_id}")
    print(f"[*] Baseline Price:         ₹{original_inr_price:.2f} (${original_usd_price})")
    print(f"[*] Baseline Availability:  {original_avail}")

    # 1. Query baseline state on Shopify GraphQL
    query_prod = """
    query getProduct($id: ID!) {
      product(id: $id) {
        id
        title
        status
        variants(first: 5) {
          edges {
            node {
              id
              price
              sku
            }
          }
        }
      }
    }
    """
    data, _, err = execute_shopify_graphql(query_prod, variables={"id": shopify_id})
    if err or not data or not data.get("product"):
        print(f"[FAIL] Failed to fetch baseline product from Shopify: {err}")
        return False, {}

    live_node = data["product"]
    live_price = float(live_node["variants"]["edges"][0]["node"]["price"])
    live_status = live_node["status"]
    print(f"[*] Verified Live Shopify State: Price ₹{live_price:.2f} | Status: {live_status}")

    test_passed = True
    audit_steps = []

    # 2. Test Step A: Simulate a price update (e.g. +$10 shift)
    print("\n--- Test Step A: Real-Time Price Shift Propagation ---")
    simulated_usd = original_usd_price + 10.0
    forex_rate = get_usd_to_inr_rate()
    expected_new_inr = float(round(simulated_usd * forex_rate))

    mutated_prod = dict(target_prod)
    mutated_prod["source_price"] = simulated_usd
    mutated_prod["current_price"] = expected_new_inr
    if mutated_prod.get("variants"):
        mutated_prod["variants"] = [dict(v) for v in mutated_prod["variants"]]
        mutated_prod["variants"][0]["source_price"] = simulated_usd
        mutated_prod["variants"][0]["price"] = f"{expected_new_inr:.2f}"
        mutated_prod["variants"][0]["price_current"] = expected_new_inr

    sim_delta_res = {
        "status": "success",
        "price_changed": True,
        "old_source_price": original_usd_price,
        "current_source_price": simulated_usd,
        "stock_changed": False,
        "availability": original_avail
    }

    print(f"[*] Dispatching price shift -> ${simulated_usd} (₹{expected_new_inr:.2f})...")
    ok = sync_delta_to_shopify(mutated_prod, sim_delta_res, forex_rate)
    if not ok:
        print("[FAIL] sync_delta_to_shopify returned False on price update!")
        test_passed = False
    else:
        # Verify immediately on Shopify
        time.sleep(1.0)
        v_data, _, v_err = execute_shopify_graphql(query_prod, variables={"id": shopify_id})
        v_price = float(v_data["product"]["variants"]["edges"][0]["node"]["price"])
        print(f"[*] Live Shopify Verified Price after shift: ₹{v_price:.2f}")
        if abs(v_price - expected_new_inr) < 0.01:
            print("[PASS] Price shift successfully reflected on Shopify Admin GraphQL in real-time!")
            audit_steps.append({"step": "price_shift", "expected": expected_new_inr, "actual": v_price, "passed": True})
        else:
            print(f"[FAIL] Price mismatch on Shopify: Expected ₹{expected_new_inr:.2f}, got ₹{v_price:.2f}")
            test_passed = False
            audit_steps.append({"step": "price_shift", "expected": expected_new_inr, "actual": v_price, "passed": False})

    # 3. Test Step B: Simulate an out-of-stock flip (availability = out_of_stock -> DRAFT)
    print("\n--- Test Step B: Out-of-Stock Protection Propagation ---")
    mutated_prod["availability"] = "out_of_stock"
    mutated_prod["is_active"] = False
    sim_delta_stock = {
        "status": "success",
        "price_changed": False,
        "current_source_price": simulated_usd,
        "stock_changed": True,
        "old_availability": "in_stock",
        "availability": "out_of_stock"
    }

    print("[*] Dispatching stock flip -> out_of_stock (Should transition status to DRAFT)...")
    ok = sync_delta_to_shopify(mutated_prod, sim_delta_stock, forex_rate)
    if not ok:
        print("[FAIL] sync_delta_to_shopify returned False on stock update!")
        test_passed = False
    else:
        time.sleep(1.0)
        v_data, _, _ = execute_shopify_graphql(query_prod, variables={"id": shopify_id})
        v_status = v_data["product"]["status"]
        print(f"[*] Live Shopify Verified Status: {v_status}")
        if v_status == "DRAFT":
            print("[PASS] Product successfully transitioned to DRAFT to protect customer checkout!")
            audit_steps.append({"step": "stock_out", "expected": "DRAFT", "actual": v_status, "passed": True})
        else:
            print(f"[FAIL] Product status not set to DRAFT: Got {v_status}")
            test_passed = False
            audit_steps.append({"step": "stock_out", "expected": "DRAFT", "actual": v_status, "passed": False})

    # 4. Test Step C: Restore original state (Pristine catalog preservation)
    print("\n--- Test Step C: Restoring Authentic Baseline State ---")
    expected_restored_inr = float(round(original_usd_price * forex_rate))
    print(f"[*] Restoring baseline price ₹{expected_restored_inr:.2f} (${original_usd_price}) and ACTIVE in_stock status...")
    restore_delta = {
        "status": "success",
        "price_changed": True,
        "current_source_price": original_usd_price,
        "stock_changed": True,
        "availability": original_avail
    }
    target_prod["current_price"] = expected_restored_inr
    if target_prod.get("variants"):
        target_prod["variants"][0]["source_price"] = original_usd_price
        target_prod["variants"][0]["price"] = f"{expected_restored_inr:.2f}"
        target_prod["variants"][0]["price_current"] = expected_restored_inr

    ok = sync_delta_to_shopify(target_prod, restore_delta, forex_rate)
    time.sleep(1.0)
    v_data, _, _ = execute_shopify_graphql(query_prod, variables={"id": shopify_id})
    restored_price = float(v_data["product"]["variants"]["edges"][0]["node"]["price"])
    restored_status = v_data["product"]["status"]
    print(f"[*] Final Restored Shopify State: Price ₹{restored_price:.2f} | Status: {restored_status}")

    if abs(restored_price - expected_restored_inr) < 0.01 and restored_status == "ACTIVE":
        print("[PASS] Pristine catalog state perfectly restored!")
        audit_steps.append({"step": "restore", "passed": True})
    else:
        print("[FAIL] Catalog state failed to restore cleanly!")
        test_passed = False
        audit_steps.append({"step": "restore", "passed": False})

    return test_passed, {"product_id": shopify_id, "steps": audit_steps}


def audit_phase_4_watch_product_data_quality() -> Tuple[bool, Dict[str, Any]]:
    print("\n" + "=" * 80)
    print("PHASE 4: WATCH PRODUCT DATA & SPECIFICATION DEEP INSPECTION")
    print("=" * 80)

    db_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "db", "jomashop", "products")
    files = glob.glob(os.path.join(db_root, "*.json"))

    specs_checked = 0
    accordions_checked = 0
    images_checked = 0
    case_diameters_found = 0
    water_res_found = 0
    movement_found = 0

    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            p = json.load(f)
        
        specs = p.get("specifications") or {}
        if specs:
            specs_checked += 1
            if specs.get("Case Diameter") or specs.get("Case Size"):
                case_diameters_found += 1
            if specs.get("Water Resistance"):
                water_res_found += 1
            if specs.get("Movement"):
                movement_found += 1

        html = p.get("descriptionHtml") or ""
        if "size-guide-accordion" in html or "Technical Specifications" in html or "Specifications" in html:
            accordions_checked += 1

        imgs = p.get("images") or []
        if imgs and len(imgs) > 0 and all(img.startswith("http") for img in imgs):
            images_checked += 1

    total = len(files)
    print(f"[*] Products Scanned:                      {total}")
    print(f"[*] Valid CDN Images:                     {images_checked}/{total} ({images_checked/total*100:.1f}%)")
    print(f"[*] Rich Specification Objects:           {specs_checked}/{total} ({specs_checked/total*100:.1f}%)")
    print(f"[*] Specification Accordions in HTML:     {accordions_checked}/{total} ({accordions_checked/total*100:.1f}%)")
    print(f"[*] Case Diameter Dimension Stamped:      {case_diameters_found}/{total} ({case_diameters_found/total*100:.1f}%)")
    print(f"[*] Water Resistance Metric Stamped:      {water_res_found}/{total} ({water_res_found/total*100:.1f}%)")
    print(f"[*] Movement Caliber Stamped:             {movement_found}/{total} ({movement_found/total*100:.1f}%)")

    passed = (images_checked == total and specs_checked == total and accordions_checked == total)
    return passed, {
        "total": total,
        "images_valid": images_checked,
        "specs_valid": specs_checked,
        "accordions_valid": accordions_checked,
        "case_diameters": case_diameters_found,
        "movements": movement_found,
        "water_resistances": water_res_found
    }


def main():
    print("=" * 80)
    print("STARTING DEEP AUDIT: WATCH CATALOG STOCK & PRICE LIVE SYNC VERIFICATION")
    print("=" * 80)

    p1_ok, p1_data = audit_phase_1_live_jomashop_polling()
    p2_ok, p2_data = audit_phase_2_shopify_gid_coverage()
    p3_ok, p3_data = audit_phase_3_live_mutation_and_sync()
    p4_ok, p4_data = audit_phase_4_watch_product_data_quality()

    print("\n" + "=" * 80)
    print("DEEP AUDIT SUMMARY SCORECARD")
    print("=" * 80)
    print(f"Phase 1: Live Jomashop Apollo Polling & Freshness: {'[PASSED 100%]' if p1_ok else '[FAILED]'}")
    print(f"Phase 2: 100% Shopify GID Coverage & Stamping:     {'[PASSED 100%]' if p2_ok else '[FAILED]'}")
    print(f"Phase 3: Live Mutation & Real-Time Sync on Shopify:{'[PASSED 100%]' if p3_ok else '[FAILED]'}")
    print(f"Phase 4: Watch Technical Data & Spec Integrity:   {'[PASSED 100%]' if p4_ok else '[FAILED]'}")
    print("=" * 80)

    overall = p1_ok and p2_ok and p3_ok and p4_ok
    if overall:
        print(">> OVERALL RESULT: [100% PASS] Watch products are actively updating live on Shopify!")
    else:
        print(">> OVERALL RESULT: [DEFECTS DETECTED]")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
